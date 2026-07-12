# Mistral API Strategy — Rate Limits, Model Choice, Sync vs Batch

Status: reference. All empirical facts below were verified on **2026-07-08** against our
own free-tier (Experiment plan) API key unless sourced otherwise.

## 1. Context

All Mistral traffic goes through **one shared API key** from the
`question-generation-service` backend. Rate limits are enforced **per model, per key**,
on two dimensions simultaneously — requests/second **and** tokens/minute. Whichever is
hit first returns 429. Multi-user traffic therefore shares a single bucket.

Relevant free-tier limits (from the console, 2026-07):

| Model                 | Req/s | ≈ Req/min | Tokens/min | Binding constraint        |
| --------------------- | ----- | --------- | ---------- | ------------------------- |
| mistral-large-2512    | 0.07  | ~4        | 250k       | RPS — one call every ~14s |
| mistral-medium-latest | 0.83  | ~50       | 25k        | TPM — ~500 tokens/request |
| mistral-small-2506    | 5.0   | 300       | 2.25M      | comfortable               |
| mistral-small-2603    | 0.83  | ~50       | 50k        | much tighter than 2506    |

⚠️ `mistral-*-latest` aliases move. Check which dated model the alias resolves to before
relying on a limits row; pin the dated ID if the alias would land on a worse-limited
version.

## 2. LLM call profile per quiz

| Step                                             | Model                | Calls     |
| ------------------------------------------------ | -------------------- | --------- |
| Quiz-length intent parsing (wizard)              | `MISTRAL_FAST_MODEL` | 1         |
| Topic extraction + concept map (per new thema)   | `MISTRAL_MODEL`      | 1–2       |
| Question generation (Prompt 3, 5 questions/call) | `MISTRAL_MODEL`      | ceil(n/5) |
| Judge (Prompt 4, 1 call per generated batch)     | `MISTRAL_MODEL`      | ceil(n/5) |

A 20-question quiz ≈ **8–10 `MISTRAL_MODEL` calls** (+ retries on judge-rejected
batches) + 1 fast-model call. On mistral-large free-tier limits (4 req/min) that is
~2.5 minutes for **one** quiz — two concurrent users already 429. This is why model
choice and batching matter.

## 3. Model choice: mistral-small is good enough (evaluated 2026-07-08)

We ran the full production pipeline (Prompt 3 → structural checks → Prompt 4 judge →
`merge_judge_verdict`) on 3 cells × 5 questions with both models, plus an 8-question
ground-truth probe of the judge (computation traps: +10%/−10% pricing, km/h→m/s,
quicksort worst case, multi-select primes).

|                                                   | mistral-small-latest | mistral-large-latest |
| ------------------------------------------------- | -------------------- | -------------------- |
| Structurally valid                                | 15/15                | 15/15                |
| Factually correct after judge (manually verified) | 12/12 served         | comparable           |
| Judge probe: derived correct answer               | 8/8                  | 8/8                  |
| Judge probe: catches wrong stated answer          | 8/8                  | 8/8                  |
| Generation latency / call                         | 3.5–6s               | 9–13s                |

The small judge caught a real generator arithmetic error (stated 4 A, correct 2 A), an
unanswerable question referencing a non-existent snippet, and an ambiguous stem.

**Decision: `MISTRAL_MODEL=mistral-small-latest` for MVP.** Revisit if content moves to
harder domains (graduate-level math, niche facts) where a small judge may share the
generator's blind spots.

Known issue found during the eval, fixed 2026-07-11: `answers_match()` in
`services/question_validation_service.py` falsely rejected textually-identical answers
when the judge sets `requires_computation=true` but the answer has no extractable
number ("It halves", "True", "O(n log n)", "n²") — it now falls back to normalized text
comparison when numeric extraction fails, instead of failing closed.

## 4. Sync mode (current implementation)

One HTTPS call per prompt via `clients/mistral_client.py::chat_complete`; the response
arrives in the same request (seconds). Retry with exponential backoff exists
(`tenacity`, 3 attempts).

Fits: interactive calls (wizard intent parsing, thema disambiguation) and low/medium
generation volume where the outbox worker can pace calls below the per-model RPS.

Missing today (add when concurrency grows): a per-model client-side limiter
(request-bucket + token-bucket) in front of `chat_complete` so bursts queue instead of
429ing.

## 5. Batch mode

### What it is

File-based, asynchronous, 50% cheaper per token. Three steps replace the single call:

1. **Upload a JSONL file** (`client.files.upload(..., purpose="batch")`) — one line per
   request: `{"custom_id": "<ours>", "body": {<same chat-completions body as sync,
incl. response_format>}}`. Up to 1M requests/file; inline batching (no file) up to
   10k requests.
2. **Create a job**: `client.batch.jobs.create(input_files=[id], model=...,
endpoint="/v1/chat/completions")`. Model is fixed per job → generation and judge
   rounds for the same model can share a job; fast-model calls need their own.
3. **Poll** `client.batch.jobs.get(job_id)` until terminal status, **download** the
   results file, map lines back via `custom_id`. Failed lines land in a separate error
   file — retry only those.

### Availability — NOT on the free tier (verified)

Tested 2026-07-08 with our Experiment-plan key: file upload succeeds, but
`batch.jobs.create` returns **402 — "You do not have access to this service. You can
enable billing via the console."** Batch requires a paid (Scale) plan. Sources:
[batch docs](https://docs.mistral.ai/capabilities/batch/),
[pricing](https://mistral.ai/pricing/).

### Turnaround

No SLA on completion — jobs queue and finish in **minutes to hours depending on queue
depth**; the job has a `timeout_hours` (default 24h) after which unprocessed lines fail.
Results stay downloadable for 24h after completion. Design consequence: batch is for
"quiz will be ready soon, we'll notify you" and pool pre-warming — never for anything a
user is actively waiting on. We could not measure real turnaround on the free tier
(402); measure with a tiny probe job (`scratchpad batch_probe.py` pattern) once billing
is enabled, before committing UX copy to any latency promise.

## 6. Switchable design (sync ⇄ batch) — IMPLEMENTED

Implemented in `clients/completion_transport.py` (2026-07-08). The seam is the
transport, not the callers.

**How to switch** — one env var, read by pydantic-settings (env var → service `.env` →
code default), like `ENABLE_BACKGROUND_WORKERS`:

```bash
MISTRAL_BATCH_MODE=true            # default false = synchronous
MISTRAL_BATCH_POLL_INTERVAL_S=10   # optional
MISTRAL_BATCH_TIMEOUT_H=24         # optional, server-side job timeout
```

**Shape**:

- `CompletionRequest` (custom_id, system_msg, user_msg, config) +
  `CompletionTransportProtocol.complete_many(requests) -> dict[custom_id, parsed_json]`.
- `SyncTransport` — gather over `chat_complete`; the default.
- `BatchTransport` — one **inline** batch job per distinct model
  (`batch.jobs.create_async(requests=...)`, ≤10k requests; file-based flavour not
  implemented), then **polls** `jobs.get_async(job_id, inline=True)` every
  `MISTRAL_BATCH_POLL_INTERVAL_S` until a terminal status — Mistral has no completion
  webhook, so polling is the only signal. Results are read from `job.outputs` and mapped
  back by `custom_id`. Fails closed: any request without a usable result raises
  `AIUnavailableError`. A 402 (batch on free tier) raises with an explicit
  "enable billing or unset MISTRAL_BATCH_MODE" message.
- `get_transport()` picks the transport once per process from `MISTRAL_BATCH_MODE`;
  `QuestionService` takes it as an injectable constructor arg (tests pass fakes).

Rules preserved:

- **Always sync, never batched**: quiz-length interpretation, wizard turns, thema
  disambiguation — those call `chat_complete`/`chat_complete_samples` directly and are
  untouched by the flag.
- **Through the transport (flag-controlled)**: Prompt 3 generation and Prompt 4 judge in
  `QuestionService`.
- Current granularity is one job per pipeline round per cell (the worker consumes one
  message at a time). Cross-quiz aggregation — accumulating many pending quizzes into
  one shared job with `custom_id = {quiz_id}:{cell}:{round}` — is the next step when
  real batch volume exists, and only touches the worker, not the transport.

## 7. Decision matrix

| Situation                                                 | Mode                                                                          |
| --------------------------------------------------------- | ----------------------------------------------------------------------------- |
| MVP, free tier                                            | Sync + mistral-small + worker pacing (only option — batch is 402)             |
| Paid, users actively waiting                              | Sync for first batch of 5 (instant start), batch for the rest + pool pre-warm |
| Paid, bulk/background (pool warming, new thema ingestion) | Batch (50% cheaper, no latency pressure)                                      |
| Peak-scale (thousands of concurrent generations)          | Batch is the only documented path; sync RPS ceilings don't reach this         |
