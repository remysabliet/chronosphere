'use client';

import { useMutation } from '@tanstack/react-query';
import { Send } from 'lucide-react';
import Link from 'next/link';
import * as React from 'react';
import { toast } from 'sonner';

import {
  confirmThemaAction,
  extractThemaAction,
  refineThemaAction,
} from '@/lib/actions/thema-actions';
import { ROUTES } from '@/lib/constants';
import { isSessionExpiredError, toFriendlyErrorMessage } from '@/lib/errors';
import { cn } from '@/lib/utils';
import { SessionExpiredDialog } from '@/shared/components/auth/session-expired-dialog';
import { WizardAvatar } from '@/shared/components/wizard/wizard-avatar';
import type { ResolvedThema, ThemaExtractionResult } from '@/types/thema';
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
  | { id: string; role: 'user'; kind: 'text'; text: string };

function newId(): string {
  return Math.random().toString(36).slice(2);
}

export default function QuizWizardPage() {
  const [messages, setMessages] = React.useState<ChatMessage[]>([
    { id: 'greeting', role: 'assistant', kind: 'greeting' },
  ]);
  // Stays set even after confirmation — confirming isn't final, the learner can
  // keep correcting the topics until they're actually done.
  const [pendingExtractionId, setPendingExtractionId] = React.useState<
    string | null
  >(null);
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
      setPendingExtractionId(result.extraction_id);
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
      setPendingExtractionId(result.extraction_id);
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
      setMessages(prev => [
        ...prev,
        { id: newId(), role: 'assistant', kind: 'confirmed', result },
      ]);
    },
    onError: onMutationError,
  });

  const isThinking = extractMutation.isPending || refineMutation.isPending;
  const lastMessage = messages[messages.length - 1];
  const justConfirmed = lastMessage?.kind === 'confirmed';

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
    confirmMutation.mutate({ extractionId, chosenRank });
  }

  let placeholder = 'What do you want to learn?';
  if (pendingExtractionId) {
    placeholder = justConfirmed
      ? 'Want something else covered? Tell me below.'
      : "Tell me what's wrong, or add more detail…";
  }

  return (
    <div className='mx-auto flex h-[calc(100vh-8rem)] max-w-2xl flex-col'>
      <SessionExpiredDialog open={sessionExpired} />
      <h1 className='mb-4 text-2xl font-bold'>Create a quiz with the Wizard</h1>

      <div className='flex flex-1 flex-col overflow-hidden rounded-lg border bg-card'>
        <div className='flex-1 space-y-4 overflow-y-auto p-4'>
          {messages.map(message => (
            <MessageBubble
              key={message.id}
              message={message}
              isConfirming={confirmMutation.isPending}
              onConfirm={handleConfirm}
            />
          ))}
          {isThinking && <ThinkingBubble />}
          <div ref={bottomRef} />
        </div>

        <form
          className='flex gap-2 border-t p-4'
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
          />
          <Button
            type='submit'
            size='icon'
            disabled={isThinking || inputValue.trim().length < 2}
          >
            <Send className='size-4' />
          </Button>
        </form>
      </div>
    </div>
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

function MessageBubble({
  message,
  isConfirming,
  onConfirm,
}: {
  message: ChatMessage;
  isConfirming: boolean;
  onConfirm: (extractionId: string, chosenRank?: number) => void;
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
          <strong>{message.result.thema}</strong>.
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
          {!isShort &&
            result.alternates.map(alt => (
              <button
                key={alt.rank}
                type='button'
                onClick={() => onConfirm(result.extraction_id, alt.rank)}
                disabled={isConfirming}
                className={cn(
                  'rounded-full border px-3 py-1 text-xs transition-colors hover:bg-accent',
                  'disabled:opacity-50'
                )}
              >
                Did you mean: {alt.thema}?
              </button>
            ))}
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

  return (
    <AssistantBubble>
      <p>I couldn&apos;t quite place that — tell me a bit more below.</p>
    </AssistantBubble>
  );
}
