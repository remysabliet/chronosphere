'use client';

import { useMutation } from '@tanstack/react-query';
import {
  Check,
  Clock,
  Compass,
  Hash,
  ListChecks,
  ScrollText,
  Send,
  Sparkles,
} from 'lucide-react';
import Link from 'next/link';
import * as React from 'react';
import { toast } from 'sonner';

import {
  confirmThemaAction,
  extractThemaAction,
  generateQuestionsAction,
  interpretQuizLengthAction,
  mapConceptsAction,
  refineThemaAction,
  submitExposureAction,
} from '@/lib/actions/thema-actions';
import { ROUTES } from '@/lib/constants';
import { isSessionExpiredError, toFriendlyErrorMessage } from '@/lib/errors';
import { cn } from '@/lib/utils';
import { SessionExpiredDialog } from '@/shared/components/auth/session-expired-dialog';
import { WizardAvatar } from '@/shared/components/wizard/wizard-avatar';
import type {
  ExposureLevel,
  NonTopicKind,
  QuestionType,
  ResolvedThema,
  ThemaExtractionResult,
} from '@/types/thema';
import { Button } from '@/ui/button';
import { Input } from '@/ui/input';

// Inputs this short ("af", "if") are too thin to trust even a unanimous guess —
// confirm the thema itself before committing to a full topic list.
const SHORT_INPUT_THRESHOLD = 4;

function isShortInput(text: string): boolean {
  return text.trim().length <= SHORT_INPUT_THRESHOLD;
}

type ChatMessage =
  | { id: string; role: 'assistant'; kind: 'greeting' }
  | {
      id: string;
      role: 'assistant';
      kind: 'result';
      result: ThemaExtractionResult;
      sourceText: string;
    }
  | {
      id: string;
      role: 'assistant';
      kind: 'confirmed';
      result: ResolvedThema;
      questionCount: number;
    }
  | {
      id: string;
      role: 'assistant';
      kind: 'exposure_prompt';
      extractionId: string;
    }
  | { id: string; role: 'assistant'; kind: 'quiz_length_prompt' }
  | { id: string; role: 'assistant'; kind: 'question_type_prompt' }
  | { id: string; role: 'assistant'; kind: 'wizard_text'; text: string }
  | { id: string; role: 'user'; kind: 'text'; text: string };

// Friendlier phrasing of the Step 5 exposure scale (Unseen/Recognized/Practiced/
// Mastered) that seeds BKT's P(L0) — see main-workflow.md Step 5 & 7.
const EXPOSURE_OPTIONS: { level: ExposureLevel; label: string }[] = [
  { level: 'Unseen', label: 'Never heard of it' },
  { level: 'Recognized', label: 'Heard of it, never studied' },
  { level: 'Practiced', label: 'Studied it before' },
  { level: 'Mastered', label: 'Know it well' },
];

type QuizLength =
  | { mode: 'time'; minutes: number }
  | { mode: 'count'; questions: number }
  // Both limits stand — the quiz ends at whichever hits first.
  | { mode: 'both'; minutes: number; questions: number }
  | { mode: 'unlimited' };

const QUESTION_COUNT_PRESETS = [10, 20, 30];
const MINUTES_PRESETS = [10, 20, 30];
const MIN_QUESTION_COUNT = 1;
const MAX_QUESTION_COUNT = 100;
const MIN_MINUTES = 1;
const MAX_MINUTES = 180;
const DEFAULT_QUESTION_COUNT = 10;
const DEFAULT_MINUTES = 20;

function describeQuizLength(length: QuizLength): string {
  if (length.mode === 'time') return `${length.minutes} minutes`;
  if (length.mode === 'count') return `${length.questions} questions`;
  if (length.mode === 'both')
    return `${length.questions} questions in ${length.minutes} minutes`;
  return 'No limit';
}

// Mirrors the MVP scope in docs/product/mvp.md — MCQ, multi-select MCQ,
// True/False, Fill-in-the-blank. Flashcards are a separate future type.
const QUESTION_TYPE_OPTIONS: { type: QuestionType; label: string }[] = [
  { type: 'MCQ', label: 'Multiple choice (one answer)' },
  { type: 'MCQMultiSelect', label: 'Multiple choice (several answers)' },
  { type: 'TrueFalse', label: 'True / False' },
  { type: 'FillInBlank', label: 'Fill in the blank' },
];

function describeQuestionTypes(types: QuestionType[]): string {
  return types
    .map(t => QUESTION_TYPE_OPTIONS.find(o => o.type === t)?.label ?? t)
    .join(', ');
}

// Each generation call produces one fixed-size batch (BATCH_SIZE in
// question_generation_service/schemas/question.py) — used only to estimate
// how many batches are needed to roughly cover the chosen quiz length.
const QUESTIONS_PER_BATCH = 5;
const SECONDS_PER_QUESTION_ESTIMATE = 45;
const UNLIMITED_TARGET_QUESTION_COUNT = 20;

function targetQuestionCount(length: QuizLength): number {
  if (length.mode === 'count' || length.mode === 'both')
    return length.questions;
  if (length.mode === 'time') {
    return Math.max(
      1,
      Math.round((length.minutes * 60) / SECONDS_PER_QUESTION_ESTIMATE)
    );
  }
  return UNLIMITED_TARGET_QUESTION_COUNT;
}

function newId(): string {
  return Math.random().toString(36).slice(2);
}

function nonTopicFallback(kind: NonTopicKind): string {
  if (kind === 'greeting_or_chitchat')
    return "Hey there! 👋 Tell me what you'd like to learn — a subject, a keyword, or paste a text.";
  if (kind === 'meta_question')
    return "I'm the quiz wizard — name any subject and I'll turn it into an adaptive quiz. What would you like to learn?";
  return "I couldn't make sense of that — try naming a subject or pasting a short text.";
}

type ResultMessage = Extract<ChatMessage, { kind: 'result' }>;

function isResolvedMessage(
  m: ChatMessage
): m is ResultMessage & { result: ResolvedThema } {
  return m.kind === 'result' && m.result.status === 'resolved';
}

const QUEST_STEPS = [
  {
    icon: Compass,
    title: 'Describe your topic',
    description: 'Tell the wizard what you want to learn.',
  },
  {
    icon: Sparkles,
    title: 'Refine & confirm',
    description: 'Narrow down the exact topic and subtopics.',
  },
  {
    icon: Clock,
    title: 'Set quiz length',
    description: 'Pick a time budget or a number of questions.',
  },
  {
    icon: ListChecks,
    title: 'Choose question types',
    description: 'Pick which formats to include.',
  },
  {
    icon: Check,
    title: 'Ready to quiz',
    description: "Locked in — you're set.",
  },
] as const;

export default function QuizWizardPage() {
  const [messages, setMessages] = React.useState<ChatMessage[]>([
    { id: 'greeting', role: 'assistant', kind: 'greeting' },
  ]);
  // Stays set even after confirmation — confirming isn't final, the learner can
  // keep correcting the topics until they're actually done.
  const [pendingExtractionId, setPendingExtractionId] = React.useState<
    string | null
  >(null);
  const [confirmClicked, setConfirmClicked] = React.useState(false);
  const [quizLength, setQuizLength] = React.useState<QuizLength | undefined>(
    undefined
  );
  const [questionTypes, setQuestionTypes] = React.useState<
    QuestionType[] | undefined
  >(undefined);
  // Confirmation result held back until sizing is settled (see effect below).
  const [confirmedResult, setConfirmedResult] =
    React.useState<ResolvedThema | null>(null);
  const completionShownFor = React.useRef<string | null>(null);
  const [inputValue, setInputValue] = React.useState('');
  const [sessionExpired, setSessionExpired] = React.useState(false);
  const bottomRef = React.useRef<HTMLDivElement>(null);

  function onMutationError(error: unknown) {
    if (isSessionExpiredError(error)) {
      setSessionExpired(true);
      return;
    }
    toast.error(toFriendlyErrorMessage(error));
  }

  const extractMutation = useMutation({
    mutationFn: extractThemaAction,
    onSuccess: (result, variables) => {
      // Chit-chat resolves nothing — keep any prior extraction refinable.
      if (result.status !== 'non_topic') {
        setPendingExtractionId(result.extraction_id);
      }
      setMessages(prev => [
        ...prev,
        {
          id: newId(),
          role: 'assistant',
          kind: 'result',
          result,
          sourceText: variables.raw_user_input,
        },
      ]);
    },
    onError: onMutationError,
  });

  const refineMutation = useMutation({
    mutationFn: ({
      extractionId,
      clarification,
    }: {
      extractionId: string;
      clarification: string;
    }) => refineThemaAction(extractionId, { clarification }),
    onSuccess: (result, variables) => {
      // A chit-chat "clarification" keeps the parent extraction pending.
      if (result.status !== 'non_topic') {
        setPendingExtractionId(result.extraction_id);
      }
      setMessages(prev => [
        ...prev,
        {
          id: newId(),
          role: 'assistant',
          kind: 'result',
          result,
          sourceText: variables.clarification,
        },
      ]);
    },
    onError: onMutationError,
  });

  const confirmMutation = useMutation({
    mutationFn: ({
      extractionId,
      chosenRank,
    }: {
      extractionId: string;
      chosenRank?: number;
    }) => confirmThemaAction(extractionId, { chosen_rank: chosenRank }),
    onSuccess: result => {
      setPendingExtractionId(result.extraction_id);
      // Held back: the completion bubble only shows once sizing is settled too.
      setConfirmedResult(result);
      // Exposure (Step 5) gates BKT init (Step 7) — ask first when it's not on
      // file yet; otherwise go straight to sizing, same as before.
      setMessages(prev => [
        ...prev,
        result.exposure_required
          ? {
              id: newId(),
              role: 'assistant',
              kind: 'exposure_prompt',
              extractionId: result.extraction_id,
            }
          : { id: newId(), role: 'assistant', kind: 'quiz_length_prompt' },
      ]);
    },
    onError: onMutationError,
  });

  const exposureMutation = useMutation({
    mutationFn: ({
      extractionId,
      exposureLevel,
    }: {
      extractionId: string;
      exposureLevel: ExposureLevel;
    }) => submitExposureAction(extractionId, { exposure_level: exposureLevel }),
    onSuccess: () => {
      setMessages(prev => [
        ...prev,
        { id: newId(), role: 'assistant', kind: 'quiz_length_prompt' },
      ]);
    },
    onError: onMutationError,
  });

  const lengthMutation = useMutation({
    mutationFn: interpretQuizLengthAction,
    onSuccess: result => {
      const {
        minutes,
        question_count: questionCount,
        unlimited,
        reply,
      } = result;
      // Both limits stand — the quiz ends at whichever hits first.
      const length: QuizLength | null =
        minutes !== null && questionCount !== null
          ? { mode: 'both', minutes, questions: questionCount }
          : unlimited
            ? { mode: 'unlimited' }
            : minutes !== null
              ? { mode: 'time', minutes }
              : questionCount !== null
                ? { mode: 'count', questions: questionCount }
                : null;
      if (length) {
        setQuizLength(length);
        const secondsPerQuestion =
          length.mode === 'both'
            ? Math.round((length.minutes * 60) / length.questions)
            : null;
        const paceNote =
          secondsPerQuestion !== null && secondsPerQuestion < 20
            ? ` That's a speedy ~${secondsPerQuestion}s per question!`
            : '';
        setMessages(prev => [
          ...prev,
          {
            id: newId(),
            role: 'assistant',
            kind: 'wizard_text',
            // A non-empty reply alongside a value explains an adjustment
            // (e.g. a clamped count) — prefer it over the generic ack.
            text:
              reply.trim() ||
              `Got it — ${describeQuizLength(length).toLowerCase()}!${paceNote}`,
          },
          { id: newId(), role: 'assistant', kind: 'question_type_prompt' },
        ]);
        return;
      }
      setMessages(prev => [
        ...prev,
        {
          id: newId(),
          role: 'assistant',
          kind: 'wizard_text',
          text:
            reply.trim() ||
            'Give me a time in minutes, a number of questions, or say "no limit".',
        },
      ]);
    },
    onError: onMutationError,
  });

  // Surfaced in the thinking bubble while generateMutation runs — the batch
  // loop below is several sequential AI calls and can take a while; a bare
  // "thinking" dot dance with no count reads as stuck.
  const [generationProgress, setGenerationProgress] = React.useState<{
    done: number;
    total: number;
  } | null>(null);

  // Fires once quiz length AND question types are both settled (see effect
  // below). Fetches the concepts mapped for this thema (Step 6, already
  // computed during confirm() — this just reads them back) and generates one
  // batch per concept/Bloom pair, up to roughly enough batches to cover the
  // chosen quiz length.
  const generateMutation = useMutation({
    mutationFn: async (input: {
      confirmed: ResolvedThema;
      allowedTypes: QuestionType[];
      targetCount: number;
    }) => {
      const { concepts } = await mapConceptsAction({
        thema: input.confirmed.thema,
        topics: input.confirmed.topics,
      });
      const pairs = concepts.flatMap(concept =>
        concept.bloom_levels.map(bloomLevel => ({
          conceptId: concept.id,
          conceptName: concept.concept,
          learningGoal: concept.learning_goal,
          bloomLevel,
        }))
      );
      const batchesNeeded = Math.max(
        1,
        Math.ceil(input.targetCount / QUESTIONS_PER_BATCH)
      );
      const totalBatches = Math.min(batchesNeeded, pairs.length);

      let totalStored = 0;
      let batchesDone = 0;
      setGenerationProgress({ done: 0, total: totalBatches });
      for (const pair of pairs.slice(0, batchesNeeded)) {
        const batch = await generateQuestionsAction({
          concept_id: pair.conceptId,
          concept_name: pair.conceptName,
          learning_goal: pair.learningGoal,
          bloom_level: pair.bloomLevel,
          difficulty_tier: 'medium',
          allowed_question_types: input.allowedTypes,
        });
        totalStored += batch.questions.length;
        batchesDone += 1;
        setGenerationProgress({ done: batchesDone, total: totalBatches });
      }
      return totalStored;
    },
    onSuccess: (questionCount, variables) => {
      setGenerationProgress(null);
      setMessages(prev => [
        ...prev,
        {
          id: newId(),
          role: 'assistant',
          kind: 'confirmed',
          result: variables.confirmed,
          questionCount,
        },
      ]);
    },
    onError: error => {
      setGenerationProgress(null);
      onMutationError(error);
    },
  });

  const isThinking =
    extractMutation.isPending ||
    refineMutation.isPending ||
    confirmMutation.isPending ||
    lengthMutation.isPending ||
    exposureMutation.isPending ||
    generateMutation.isPending;
  const lastMessage = messages[messages.length - 1];
  const justConfirmed = lastMessage?.kind === 'confirmed';
  // Derived from the actual last bubble shown, not from optimistic client
  // flags (e.g. confirmClicked flips true the instant a button is clicked,
  // well before the corresponding prompt bubble actually arrives) — so the
  // input placeholder and routing below never react to a step before its
  // question has actually been asked.
  const awaitingExposure = lastMessage?.kind === 'exposure_prompt';
  const awaitingQuestionTypes = lastMessage?.kind === 'question_type_prompt';
  const awaitingQuizLength = lastMessage?.kind === 'quiz_length_prompt';

  const currentStepIndex = !pendingExtractionId
    ? 0
    : !confirmClicked
      ? 1
      : !quizLength
        ? 2
        : !questionTypes
          ? 3
          : 4;
  const latestResolved = [...messages]
    .reverse()
    .find(isResolvedMessage)?.result;
  const confirmedThema =
    lastMessage?.kind === 'confirmed' ? lastMessage.result : undefined;

  // The flow is complete only once the topic is confirmed, a quiz length is
  // set, AND question types are chosen — whichever lands last triggers
  // generation, which in turn shows the completion bubble on success.
  React.useEffect(() => {
    if (!confirmedResult || !quizLength || !questionTypes) return;
    if (completionShownFor.current === confirmedResult.extraction_id) return;
    completionShownFor.current = confirmedResult.extraction_id;
    generateMutation.mutate({
      confirmed: confirmedResult,
      allowedTypes: questionTypes,
      targetCount: targetQuestionCount(quizLength),
    });
  }, [confirmedResult, quizLength, questionTypes]);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  function handleSend() {
    const text = inputValue.trim();
    if (text.length < 2 || awaitingExposure || awaitingQuestionTypes) return;

    setMessages(prev => [
      ...prev,
      { id: newId(), role: 'user', kind: 'text', text },
    ]);
    setInputValue('');

    // Step-aware routing: while the sizing question is open, typed text answers
    // the sizing question — it must never be re-interpreted as a topic.
    if (awaitingQuizLength) {
      lengthMutation.mutate(text);
      return;
    }

    if (pendingExtractionId) {
      refineMutation.mutate({
        extractionId: pendingExtractionId,
        clarification: text,
      });
    } else {
      extractMutation.mutate({ raw_user_input: text });
    }
  }

  function handleConfirm(extractionId: string, chosenRank?: number) {
    setConfirmClicked(true);
    confirmMutation.mutate({ extractionId, chosenRank });
  }

  function handleSelectExposure(extractionId: string, level: ExposureLevel) {
    const label = EXPOSURE_OPTIONS.find(o => o.level === level)?.label ?? level;
    setMessages(prev => [
      ...prev,
      { id: newId(), role: 'user', kind: 'text', text: label },
    ]);
    exposureMutation.mutate({ extractionId, exposureLevel: level });
  }

  function handleSelectQuizLength(length: QuizLength) {
    setQuizLength(length);
    setMessages(prev => [
      ...prev,
      {
        id: newId(),
        role: 'user',
        kind: 'text',
        text: describeQuizLength(length),
      },
      { id: newId(), role: 'assistant', kind: 'question_type_prompt' },
    ]);
  }

  function handleSelectQuestionTypes(types: QuestionType[]) {
    setQuestionTypes(types);
    setMessages(prev => [
      ...prev,
      {
        id: newId(),
        role: 'user',
        kind: 'text',
        text: describeQuestionTypes(types),
      },
    ]);
  }

  let placeholder = 'What do you want to learn?';
  if (awaitingExposure) {
    placeholder = 'Pick one above';
  } else if (awaitingQuestionTypes) {
    placeholder = 'Pick at least one above';
  } else if (awaitingQuizLength) {
    placeholder = 'e.g. "15 minutes", "10 questions", or "no limit"';
  } else if (pendingExtractionId) {
    placeholder = justConfirmed
      ? 'Want something else covered? Tell me below.'
      : "Tell me what's wrong, or add more detail…";
  }

  return (
    <div className='relative mx-auto flex h-[calc(100vh-8rem)] max-w-4xl flex-col'>
      <div
        aria-hidden
        className={cn(
          'pointer-events-none absolute inset-0 -z-10 opacity-40 blur-3xl transition-opacity duration-700',
          'bg-[radial-gradient(ellipse_60%_50%_at_50%_0%,theme(colors.primary/25%),transparent)]',
          isThinking && 'opacity-70'
        )}
      />
      <SessionExpiredDialog open={sessionExpired} />
      <h1 className='mb-4 text-2xl font-bold'>Create a quiz with the Wizard</h1>

      <div className='flex min-h-0 flex-1 gap-6 overflow-hidden'>
        <div className='flex min-h-0 flex-1 flex-col overflow-hidden'>
          <div className='min-h-0 flex-1 space-y-4 overflow-y-auto px-1 py-4'>
            {messages.map(message => (
              <MessageBubble
                key={message.id}
                message={message}
                isConfirming={confirmMutation.isPending}
                onConfirm={handleConfirm}
                quizLength={quizLength}
                onSelectQuizLength={handleSelectQuizLength}
                isSubmittingExposure={exposureMutation.isPending}
                onSelectExposure={handleSelectExposure}
                questionTypes={questionTypes}
                onSelectQuestionTypes={handleSelectQuestionTypes}
              />
            ))}
            {isThinking && (
              <ThinkingBubble
                label={
                  generationProgress
                    ? `Generating questions… (${generationProgress.done}/${generationProgress.total})`
                    : undefined
                }
              />
            )}
            <div ref={bottomRef} />
          </div>

          <form
            className='flex shrink-0 gap-2 rounded-full border bg-card/80 p-2 shadow-lg backdrop-blur'
            onSubmit={e => {
              e.preventDefault();
              handleSend();
            }}
          >
            <Input
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              aria-label='Message'
              placeholder={placeholder}
              disabled={isThinking || awaitingExposure || awaitingQuestionTypes}
              className='rounded-full border-none bg-transparent shadow-none focus-visible:ring-0'
            />
            <Button
              type='submit'
              size='icon'
              className='shrink-0 rounded-full'
              disabled={
                isThinking ||
                awaitingExposure ||
                awaitingQuestionTypes ||
                inputValue.trim().length < 2
              }
            >
              <Send className='size-4' />
            </Button>
          </form>
        </div>

        <QuestLog
          currentStepIndex={currentStepIndex}
          confirmedThema={confirmedThema}
          latestResolved={latestResolved}
        />
      </div>
    </div>
  );
}

function QuestLog({
  currentStepIndex,
  confirmedThema,
  latestResolved,
}: {
  currentStepIndex: number;
  confirmedThema?: ResolvedThema;
  latestResolved?: ResolvedThema;
}) {
  const target = confirmedThema ?? latestResolved;

  return (
    <aside className='hidden min-h-0 w-72 shrink-0 flex-col gap-4 md:flex'>
      <div className='shrink-0 rounded-2xl border bg-card/60 p-5 backdrop-blur'>
        <h2 className='mb-4 flex items-center gap-2 text-sm font-semibold text-muted-foreground'>
          <ScrollText className='size-4' />
          Quest Log
        </h2>
        <ol className='space-y-4'>
          {QUEST_STEPS.map((step, i) => {
            const isDone = i < currentStepIndex;
            const isCurrent = i === currentStepIndex;
            const Icon = step.icon;
            return (
              <li key={step.title} className='flex gap-3'>
                <span
                  className={cn(
                    'flex size-6 shrink-0 items-center justify-center rounded-full border',
                    isDone &&
                      'border-primary bg-primary text-primary-foreground',
                    isCurrent && 'border-primary text-primary',
                    !isDone &&
                      !isCurrent &&
                      'border-muted-foreground/30 text-muted-foreground/40'
                  )}
                >
                  <Icon className='size-3.5' />
                </span>
                <div>
                  <p
                    className={cn(
                      'text-sm font-medium',
                      !isDone && !isCurrent && 'text-muted-foreground/50'
                    )}
                  >
                    {step.title}
                  </p>
                  {isCurrent && (
                    <p className='text-xs text-muted-foreground'>
                      {step.description}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </div>

      {target && (
        <div className='flex min-h-0 flex-1 flex-col rounded-2xl border bg-card/60 p-5 backdrop-blur'>
          <p className='mb-2 shrink-0 text-xs font-semibold uppercase tracking-wide text-muted-foreground'>
            {confirmedThema ? 'Locked target' : 'Current target'}
          </p>
          <p className='mb-2 shrink-0 line-clamp-2 font-medium'>
            {target.thema}
          </p>
          <div className='min-h-0 flex-1 overflow-y-auto'>
            <TopicChips topics={target.topics} />
          </div>
        </div>
      )}
    </aside>
  );
}

function AssistantBubble({
  children,
  talking = false,
  centerTail = false,
}: {
  children: React.ReactNode;
  talking?: boolean;
  // The thinking bubble is too short to have a straight wall at the avatar's
  // fixed center (top-5) — center the tail on the bubble itself there instead.
  centerTail?: boolean;
}) {
  return (
    <div className='flex items-start gap-2'>
      <WizardAvatar size='sm' talking={talking} />
      <div className='relative max-w-[80%] rounded-lg bg-muted px-4 py-3 text-sm'>
        <span
          className={cn(
            'absolute -left-[7px] size-0 border-y-[6px] border-r-8 border-y-transparent border-r-muted',
            centerTail ? 'top-1/2 -translate-y-1/2' : 'top-5'
          )}
        />
        <div className='space-y-3'>{children}</div>
      </div>
    </div>
  );
}

function ThinkingBubble({ label }: { label?: string }) {
  return (
    <AssistantBubble talking centerTail>
      <div className='flex items-center gap-2'>
        <div className='flex items-center gap-1'>
          {[0, 1, 2].map(i => (
            <span
              key={i}
              className='size-1.5 animate-bounce rounded-full bg-muted-foreground'
              style={{ animationDelay: `${i * 0.12}s` }}
            />
          ))}
        </div>
        {label && (
          <span className='text-xs text-muted-foreground'>{label}</span>
        )}
      </div>
    </AssistantBubble>
  );
}

function TopicChips({ topics }: { topics: string[] }) {
  return (
    <div className='flex flex-wrap gap-1.5'>
      {topics.map(topic => (
        <span
          key={topic}
          className='rounded-full bg-background px-2.5 py-1 text-xs'
        >
          {topic}
        </span>
      ))}
    </div>
  );
}

function initialLimitByCount(value: QuizLength | undefined): boolean {
  return value?.mode === 'count' || value?.mode === 'both';
}

function initialLimitByTime(value: QuizLength | undefined): boolean {
  return value?.mode === 'time' || value?.mode === 'both';
}

function initialQuestionCount(value: QuizLength | undefined): number {
  if (value?.mode === 'count' || value?.mode === 'both') return value.questions;
  return DEFAULT_QUESTION_COUNT;
}

function initialMinutes(value: QuizLength | undefined): number {
  if (value?.mode === 'time' || value?.mode === 'both') return value.minutes;
  return DEFAULT_MINUTES;
}

function clampNumber(value: number, min: number, max: number): number {
  if (Number.isNaN(value)) return min;
  return Math.min(max, Math.max(min, Math.round(value)));
}

function QuizLengthPicker({
  value,
  onConfirm,
}: {
  value?: QuizLength;
  onConfirm: (length: QuizLength) => void;
}) {
  const locked = value !== undefined;
  const [limitByCount, setLimitByCount] = React.useState(
    initialLimitByCount(value)
  );
  const [questionCount, setQuestionCount] = React.useState(
    initialQuestionCount(value)
  );
  const [limitByTime, setLimitByTime] = React.useState(
    initialLimitByTime(value)
  );
  const [minutes, setMinutes] = React.useState(initialMinutes(value));

  function handleContinue() {
    if (limitByCount && limitByTime) {
      onConfirm({ mode: 'both', questions: questionCount, minutes });
    } else if (limitByCount) {
      onConfirm({ mode: 'count', questions: questionCount });
    } else if (limitByTime) {
      onConfirm({ mode: 'time', minutes });
    } else {
      onConfirm({ mode: 'unlimited' });
    }
  }

  return (
    <div className='space-y-3'>
      <div
        className={cn(
          'rounded-xl border p-3 transition-colors',
          limitByCount ? 'border-primary/50 bg-primary/5' : 'border-border'
        )}
      >
        <label className='flex cursor-pointer items-center gap-2 text-sm font-medium'>
          <input
            type='checkbox'
            checked={limitByCount}
            disabled={locked}
            onChange={e => setLimitByCount(e.target.checked)}
            className='size-4 rounded border-muted-foreground/40 accent-primary disabled:cursor-not-allowed'
          />
          <Hash className='size-3.5 text-muted-foreground' />
          Limit by number of questions
        </label>
        {limitByCount && (
          <div className='mt-2 flex flex-wrap items-center gap-1.5 pl-6'>
            <Input
              type='number'
              inputMode='numeric'
              min={MIN_QUESTION_COUNT}
              max={MAX_QUESTION_COUNT}
              value={questionCount}
              disabled={locked}
              onChange={e =>
                setQuestionCount(
                  clampNumber(
                    Number(e.target.value),
                    MIN_QUESTION_COUNT,
                    MAX_QUESTION_COUNT
                  )
                )
              }
              className='h-8 w-20 rounded-full text-center'
            />
            <span className='text-sm text-muted-foreground'>questions</span>
            {!locked &&
              QUESTION_COUNT_PRESETS.map(preset => (
                <Button
                  key={preset}
                  type='button'
                  size='sm'
                  variant={questionCount === preset ? 'default' : 'outline'}
                  onClick={() => setQuestionCount(preset)}
                >
                  {preset}
                </Button>
              ))}
          </div>
        )}
      </div>

      <div
        className={cn(
          'rounded-xl border p-3 transition-colors',
          limitByTime ? 'border-primary/50 bg-primary/5' : 'border-border'
        )}
      >
        <label className='flex cursor-pointer items-center gap-2 text-sm font-medium'>
          <input
            type='checkbox'
            checked={limitByTime}
            disabled={locked}
            onChange={e => setLimitByTime(e.target.checked)}
            className='size-4 rounded border-muted-foreground/40 accent-primary disabled:cursor-not-allowed'
          />
          <Clock className='size-3.5 text-muted-foreground' />
          Limit by time
        </label>
        {limitByTime && (
          <div className='mt-2 flex flex-wrap items-center gap-1.5 pl-6'>
            <Input
              type='number'
              inputMode='numeric'
              min={MIN_MINUTES}
              max={MAX_MINUTES}
              value={minutes}
              disabled={locked}
              onChange={e =>
                setMinutes(
                  clampNumber(Number(e.target.value), MIN_MINUTES, MAX_MINUTES)
                )
              }
              className='h-8 w-20 rounded-full text-center'
            />
            <span className='text-sm text-muted-foreground'>minutes</span>
            {!locked &&
              MINUTES_PRESETS.map(preset => (
                <Button
                  key={preset}
                  type='button'
                  size='sm'
                  variant={minutes === preset ? 'default' : 'outline'}
                  onClick={() => setMinutes(preset)}
                >
                  {preset}
                </Button>
              ))}
          </div>
        )}
      </div>

      {!locked && (
        <Button type='button' size='sm' onClick={handleContinue}>
          Continue
        </Button>
      )}
    </div>
  );
}

function QuestionTypePicker({
  value,
  onConfirm,
}: {
  value?: QuestionType[];
  onConfirm: (types: QuestionType[]) => void;
}) {
  const [selected, setSelected] = React.useState<QuestionType[]>(value ?? []);

  function toggle(type: QuestionType) {
    setSelected(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
    );
  }

  return (
    <div className='space-y-3'>
      <div className='flex flex-wrap gap-1.5'>
        {QUESTION_TYPE_OPTIONS.map(({ type, label }) => (
          <Button
            key={type}
            type='button'
            size='sm'
            variant={selected.includes(type) ? 'default' : 'outline'}
            disabled={value !== undefined}
            onClick={() => toggle(type)}
          >
            {label}
          </Button>
        ))}
      </div>
      {value === undefined && (
        <Button
          type='button'
          size='sm'
          disabled={selected.length === 0}
          onClick={() => onConfirm(selected)}
        >
          Continue
        </Button>
      )}
    </div>
  );
}

function MessageBubble({
  message,
  isConfirming,
  onConfirm,
  quizLength,
  onSelectQuizLength,
  isSubmittingExposure,
  onSelectExposure,
  questionTypes,
  onSelectQuestionTypes,
}: {
  message: ChatMessage;
  isConfirming: boolean;
  onConfirm: (extractionId: string, chosenRank?: number) => void;
  quizLength?: QuizLength;
  onSelectQuizLength: (length: QuizLength) => void;
  isSubmittingExposure: boolean;
  onSelectExposure: (extractionId: string, level: ExposureLevel) => void;
  questionTypes?: QuestionType[];
  onSelectQuestionTypes: (types: QuestionType[]) => void;
}) {
  if (message.role === 'user') {
    return (
      <div className='flex justify-end'>
        <div className='max-w-[80%] rounded-2xl rounded-tr-sm bg-primary px-4 py-3 text-sm text-primary-foreground'>
          {message.text}
        </div>
      </div>
    );
  }

  if (message.kind === 'greeting') {
    return (
      <AssistantBubble>
        Hi! I&apos;m here to help you build a quiz. What do you want to learn
        today?
      </AssistantBubble>
    );
  }

  if (message.kind === 'confirmed') {
    return (
      <AssistantBubble>
        <p>
          Locked in — you&apos;ll be quizzed on{' '}
          <strong>{message.result.thema}</strong>
          {quizLength
            ? ` (${describeQuizLength(quizLength).toLowerCase()})`
            : ''}
          .
        </p>
        <p>
          {message.questionCount > 0
            ? `${message.questionCount} question${message.questionCount === 1 ? '' : 's'} ready.`
            : "Hmm, no questions made it through validation — you can still explore what's mapped so far."}
        </p>
        <p className='text-xs text-muted-foreground'>
          Want something else covered? Tell me below — or head to your dashboard
          when you&apos;re ready.
        </p>
        <Button asChild size='sm'>
          <Link href={ROUTES.DASHBOARD}>Back to dashboard</Link>
        </Button>
      </AssistantBubble>
    );
  }

  if (message.kind === 'exposure_prompt') {
    return (
      <AssistantBubble>
        <p>How familiar are you with this already?</p>
        <div className='flex flex-wrap gap-1.5'>
          {EXPOSURE_OPTIONS.map(({ level, label }) => (
            <Button
              key={level}
              type='button'
              size='sm'
              variant='outline'
              disabled={isSubmittingExposure}
              onClick={() => onSelectExposure(message.extractionId, level)}
            >
              {label}
            </Button>
          ))}
        </div>
      </AssistantBubble>
    );
  }

  if (message.kind === 'quiz_length_prompt') {
    return (
      <AssistantBubble>
        <p>How do you want to size the quiz?</p>
        <QuizLengthPicker value={quizLength} onConfirm={onSelectQuizLength} />
      </AssistantBubble>
    );
  }

  if (message.kind === 'question_type_prompt') {
    return (
      <AssistantBubble>
        <p>What kind of questions do you want? Pick one or more.</p>
        <QuestionTypePicker
          value={questionTypes}
          onConfirm={onSelectQuestionTypes}
        />
      </AssistantBubble>
    );
  }

  if (message.kind === 'wizard_text') {
    return (
      <AssistantBubble>
        <p>{message.text}</p>
      </AssistantBubble>
    );
  }

  const { result, sourceText } = message;

  if (result.status === 'resolved') {
    const isShort = isShortInput(sourceText);
    return (
      <AssistantBubble>
        {isShort ? (
          <p>
            By &ldquo;{sourceText}&rdquo;, do you mean{' '}
            <strong>{result.thema}</strong>?
          </p>
        ) : (
          <>
            <p>{result.confirmation}</p>
            <TopicChips topics={result.topics} />
          </>
        )}
        <div className='flex flex-wrap items-center gap-2 pt-1'>
          <Button
            size='sm'
            onClick={() => onConfirm(result.extraction_id, 1)}
            disabled={isConfirming}
          >
            Yes, that&apos;s right
          </Button>
        </div>
        <p className='text-xs text-muted-foreground'>
          {isShort
            ? 'Not quite? Just tell me below.'
            : 'Do these topics look right? Tell me below if you want something different.'}
        </p>
      </AssistantBubble>
    );
  }

  if (result.status === 'ambiguous') {
    return (
      <AssistantBubble>
        <p>Which one did you mean?</p>
        {result.candidates.map(candidate => (
          <div
            key={candidate.rank}
            className='space-y-1.5 rounded-lg bg-background p-3'
          >
            <p className='font-medium'>{candidate.thema}</p>
            <p className='text-xs text-muted-foreground'>
              {candidate.confirmation}
            </p>
            <Button
              size='sm'
              variant='outline'
              onClick={() => onConfirm(result.extraction_id, candidate.rank)}
              disabled={isConfirming}
            >
              This one
            </Button>
          </div>
        ))}
        <p className='text-xs text-muted-foreground'>
          None of these? Just tell me more below.
        </p>
      </AssistantBubble>
    );
  }

  if (result.status === 'non_topic') {
    return (
      <AssistantBubble>
        <p>{result.reply.trim() || nonTopicFallback(result.input_kind)}</p>
      </AssistantBubble>
    );
  }

  return (
    <AssistantBubble>
      <p>I couldn&apos;t quite place that — tell me a bit more below.</p>
    </AssistantBubble>
  );
}
