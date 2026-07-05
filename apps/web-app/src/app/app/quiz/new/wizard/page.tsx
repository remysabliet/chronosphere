'use client';

import { useMutation } from '@tanstack/react-query';
import {
  Check,
  Clock,
  Compass,
  Hash,
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
  interpretQuizLengthAction,
  refineThemaAction,
} from '@/lib/actions/thema-actions';
import { ROUTES } from '@/lib/constants';
import { isSessionExpiredError, toFriendlyErrorMessage } from '@/lib/errors';
import { cn } from '@/lib/utils';
import { SessionExpiredDialog } from '@/shared/components/auth/session-expired-dialog';
import { WizardAvatar } from '@/shared/components/wizard/wizard-avatar';
import type {
  NonTopicKind,
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
  | { id: string; role: 'assistant'; kind: 'confirmed'; result: ResolvedThema }
  | { id: string; role: 'assistant'; kind: 'quiz_length_prompt' }
  | { id: string; role: 'assistant'; kind: 'wizard_text'; text: string }
  | { id: string; role: 'user'; kind: 'text'; text: string };

type QuizLength =
  | { mode: 'time'; minutes: number }
  | { mode: 'count'; questions: number }
  // Both limits stand — the quiz ends at whichever hits first.
  | { mode: 'both'; minutes: number; questions: number }
  | { mode: 'unlimited' };

const TIME_OPTIONS = [10, 20, 30];
const COUNT_OPTIONS = [10, 20, 30];

function describeQuizLength(length: QuizLength): string {
  if (length.mode === 'time') return `${length.minutes} minutes`;
  if (length.mode === 'count') return `${length.questions} questions`;
  if (length.mode === 'both')
    return `${length.questions} questions in ${length.minutes} minutes`;
  return 'No limit';
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

  const isThinking =
    extractMutation.isPending ||
    refineMutation.isPending ||
    lengthMutation.isPending;
  const lastMessage = messages[messages.length - 1];
  const justConfirmed = lastMessage?.kind === 'confirmed';

  const currentStepIndex = !pendingExtractionId
    ? 0
    : !confirmClicked
      ? 1
      : !justConfirmed || !quizLength
        ? 2
        : 3;
  const latestResolved = [...messages]
    .reverse()
    .find(isResolvedMessage)?.result;
  const confirmedThema =
    lastMessage?.kind === 'confirmed' ? lastMessage.result : undefined;

  // The flow is complete only when BOTH the topic confirmation returned and a
  // quiz length is set — whichever lands last triggers the completion bubble.
  React.useEffect(() => {
    if (!confirmedResult || !quizLength) return;
    if (completionShownFor.current === confirmedResult.extraction_id) return;
    completionShownFor.current = confirmedResult.extraction_id;
    setMessages(prev => [
      ...prev,
      {
        id: newId(),
        role: 'assistant',
        kind: 'confirmed',
        result: confirmedResult,
      },
    ]);
  }, [confirmedResult, quizLength]);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  function handleSend() {
    const text = inputValue.trim();
    if (text.length < 2) return;

    setMessages(prev => [
      ...prev,
      { id: newId(), role: 'user', kind: 'text', text },
    ]);
    setInputValue('');

    // Step-aware routing: while the sizing question is open, typed text answers
    // the sizing question — it must never be re-interpreted as a topic.
    if (confirmClicked && !quizLength) {
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
    setMessages(prev => [
      ...prev,
      { id: newId(), role: 'assistant', kind: 'quiz_length_prompt' },
    ]);
    confirmMutation.mutate({ extractionId, chosenRank });
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
    ]);
  }

  let placeholder = 'What do you want to learn?';
  if (confirmClicked && !quizLength) {
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
              />
            ))}
            {isThinking && <ThinkingBubble />}
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
              disabled={isThinking}
              className='rounded-full border-none bg-transparent shadow-none focus-visible:ring-0'
            />
            <Button
              type='submit'
              size='icon'
              className='shrink-0 rounded-full'
              disabled={isThinking || inputValue.trim().length < 2}
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

function ThinkingBubble() {
  return (
    <AssistantBubble talking centerTail>
      <div className='flex items-center gap-1'>
        {[0, 1, 2].map(i => (
          <span
            key={i}
            className='size-1.5 animate-bounce rounded-full bg-muted-foreground'
            style={{ animationDelay: `${i * 0.12}s` }}
          />
        ))}
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

function quizLengthEquals(a: QuizLength, b: QuizLength): boolean {
  if (a.mode !== b.mode) return false;
  if (a.mode === 'time' && b.mode === 'time') return a.minutes === b.minutes;
  if (a.mode === 'count' && b.mode === 'count')
    return a.questions === b.questions;
  return a.mode === 'unlimited' && b.mode === 'unlimited';
}

function QuizLengthPicker({
  value,
  onSelect,
}: {
  value?: QuizLength;
  onSelect: (length: QuizLength) => void;
}) {
  function variantFor(length: QuizLength) {
    return value && quizLengthEquals(value, length) ? 'default' : 'outline';
  }

  return (
    <div className='space-y-3'>
      <div>
        <p className='mb-1.5 flex items-center gap-1 text-xs font-medium text-muted-foreground'>
          <Clock className='size-3' />
          By time
        </p>
        <div className='flex flex-wrap gap-1.5'>
          {TIME_OPTIONS.map(minutes => (
            <Button
              key={minutes}
              type='button'
              size='sm'
              variant={variantFor({ mode: 'time', minutes })}
              onClick={() => onSelect({ mode: 'time', minutes })}
            >
              {minutes} min
            </Button>
          ))}
        </div>
      </div>
      <div>
        <p className='mb-1.5 flex items-center gap-1 text-xs font-medium text-muted-foreground'>
          <Hash className='size-3' />
          By question count
        </p>
        <div className='flex flex-wrap gap-1.5'>
          {COUNT_OPTIONS.map(questions => (
            <Button
              key={questions}
              type='button'
              size='sm'
              variant={variantFor({ mode: 'count', questions })}
              onClick={() => onSelect({ mode: 'count', questions })}
            >
              {questions} questions
            </Button>
          ))}
        </div>
      </div>
      <Button
        type='button'
        size='sm'
        variant={variantFor({ mode: 'unlimited' })}
        onClick={() => onSelect({ mode: 'unlimited' })}
      >
        No limit
      </Button>
    </div>
  );
}

function MessageBubble({
  message,
  isConfirming,
  onConfirm,
  quizLength,
  onSelectQuizLength,
}: {
  message: ChatMessage;
  isConfirming: boolean;
  onConfirm: (extractionId: string, chosenRank?: number) => void;
  quizLength?: QuizLength;
  onSelectQuizLength: (length: QuizLength) => void;
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

  if (message.kind === 'quiz_length_prompt') {
    return (
      <AssistantBubble>
        <p>How do you want to size the quiz?</p>
        <QuizLengthPicker value={quizLength} onSelect={onSelectQuizLength} />
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
