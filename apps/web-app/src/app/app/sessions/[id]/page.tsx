'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { CheckCircle2, XCircle } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import * as React from 'react';
import { toast } from 'sonner';

import {
  getSessionAction,
  getSessionReviewAction,
  submitAnswerAction,
} from '@/lib/actions/session-actions';
import { ROUTES } from '@/lib/constants';
import { isSessionExpiredError, toFriendlyErrorMessage } from '@/lib/errors';
import { cn } from '@/lib/utils';
import { SessionExpiredDialog } from '@/shared/components/auth/session-expired-dialog';
import { SessionResults } from '@/shared/components/quiz/session-results';
import type {
  AnswerResult,
  SessionQuestion,
  SessionState,
} from '@/types/session';
import { Button } from '@/ui/button';
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/ui/card';
import { Input } from '@/ui/input';

export default function SessionPage() {
  const params = useParams<{ id: string }>();
  const sessionId = params.id;

  const {
    data: initialState,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => getSessionAction(sessionId),
    // `state` below is seeded from this once and then advanced locally from
    // mutation responses — a background refetch (e.g. on window refocus)
    // would otherwise update `initialState` silently while the `prev ?? ...`
    // guard ignores it, an invisible mismatch between the two. Disabling
    // background refetches keeps them in sync by construction.
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const [state, setState] = React.useState<SessionState | null>(null);
  const [feedback, setFeedback] = React.useState<AnswerResult | null>(null);
  const [selected, setSelected] = React.useState<string[]>([]);
  const [startedAt, setStartedAt] = React.useState(() => Date.now());
  const [sessionExpired, setSessionExpired] = React.useState(false);

  React.useEffect(() => {
    if (initialState) setState(prev => prev ?? initialState);
  }, [initialState]);

  function advance(nextState: SessionState) {
    setState(nextState);
    setFeedback(null);
    setSelected([]);
    setStartedAt(Date.now());
  }

  const submitMutation = useMutation({
    mutationFn: (question: SessionQuestion) =>
      submitAnswerAction(sessionId, {
        question_id: question.id,
        selected,
        response_time_seconds: Math.round((Date.now() - startedAt) / 1000),
      }),
    onSuccess: result => {
      // Outside immediate mode the backend redacts grading — advance
      // silently instead of pausing on an empty feedback panel.
      if (result.state.feedback_mode === 'immediate') {
        setFeedback(result);
      } else {
        advance(result.state);
      }
    },
    onError: (error: unknown) => {
      if (isSessionExpiredError(error)) {
        setSessionExpired(true);
        return;
      }
      toast.error(toFriendlyErrorMessage(error));
    },
  });

  const reviewQuery = useQuery({
    queryKey: ['session-review', sessionId],
    queryFn: () => getSessionReviewAction(sessionId),
    enabled: state?.session_complete === true,
  });

  function handleNext() {
    if (!feedback) return;
    advance(feedback.state);
  }

  if (isLoading || !state) {
    return <p className='text-muted-foreground'>Loading…</p>;
  }

  if (isError) {
    return (
      <p className='text-muted-foreground'>
        This session couldn&apos;t be loaded.
      </p>
    );
  }

  return (
    <div className='mx-auto max-w-2xl space-y-6'>
      <SessionExpiredDialog open={sessionExpired} />

      {state.session_complete ? (
        reviewQuery.data ? (
          <SessionResults review={reviewQuery.data} />
        ) : reviewQuery.isError ? (
          <ResultsError
            correctCount={state.correct_count}
            totalQuestions={state.total_questions}
            isRetrying={reviewQuery.isFetching}
            onRetry={() => reviewQuery.refetch()}
          />
        ) : (
          <p className='text-muted-foreground'>Preparing your results…</p>
        )
      ) : (
        <ActiveQuestion
          state={state}
          feedback={feedback}
          selected={selected}
          onSelectedChange={setSelected}
          onSubmit={question => submitMutation.mutate(question)}
          onNext={handleNext}
          isSubmitting={submitMutation.isPending}
        />
      )}
    </div>
  );
}

function ResultsError({
  correctCount,
  totalQuestions,
  isRetrying,
  onRetry,
}: {
  correctCount: number | null;
  totalQuestions: number;
  isRetrying: boolean;
  onRetry: () => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Quiz complete!</CardTitle>
      </CardHeader>
      <CardContent className='space-y-2'>
        {correctCount !== null && (
          <p className='font-medium'>
            {correctCount} of {totalQuestions} correct
          </p>
        )}
        <p className='text-sm text-muted-foreground'>
          The detailed results couldn&apos;t be loaded.
        </p>
      </CardContent>
      <CardFooter className='gap-2'>
        <Button onClick={onRetry} disabled={isRetrying}>
          {isRetrying ? 'Retrying…' : 'Retry'}
        </Button>
        <Button asChild variant='outline'>
          <Link href={ROUTES.QUIZZES}>Back to quizzes</Link>
        </Button>
      </CardFooter>
    </Card>
  );
}

function ActiveQuestion({
  state,
  feedback,
  selected,
  onSelectedChange,
  onSubmit,
  onNext,
  isSubmitting,
}: {
  state: SessionState;
  feedback: AnswerResult | null;
  selected: string[];
  onSelectedChange: (selected: string[]) => void;
  onSubmit: (question: SessionQuestion) => void;
  onNext: () => void;
  isSubmitting: boolean;
}) {
  const question = state.question;
  if (!question) return null;

  return (
    <Card>
      <CardHeader className='space-y-3'>
        <p className='text-xs font-medium uppercase tracking-wide text-muted-foreground'>
          Question {state.current_index + 1} of {state.total_questions}
        </p>
        <div className='h-1.5 w-full overflow-hidden rounded-full bg-muted'>
          <div
            className='h-full rounded-full bg-primary transition-all'
            style={{
              width: `${(state.current_index / state.total_questions) * 100}%`,
            }}
          />
        </div>
        <CardTitle className='text-lg'>{question.question_text}</CardTitle>
      </CardHeader>
      <CardContent className='space-y-4'>
        <AnswerInput
          question={question}
          selected={selected}
          onChange={onSelectedChange}
          disabled={feedback !== null}
        />
        {feedback && feedback.is_correct !== null && (
          <div
            className={cn(
              'flex items-start gap-2 rounded-lg border p-3 text-sm',
              feedback.is_correct
                ? 'border-green-500/30 bg-green-500/10 text-green-700 dark:text-green-400'
                : 'border-destructive/30 bg-destructive/10 text-destructive'
            )}
          >
            {feedback.is_correct ? (
              <CheckCircle2 className='mt-0.5 size-4 shrink-0' />
            ) : (
              <XCircle className='mt-0.5 size-4 shrink-0' />
            )}
            <div>
              <p className='font-medium'>
                {feedback.is_correct
                  ? 'Correct!'
                  : `Correct answer: ${(feedback.correct_answers ?? []).join(', ')}`}
              </p>
              {feedback.explanation && (
                <p className='mt-1 text-muted-foreground'>
                  {feedback.explanation}
                </p>
              )}
            </div>
          </div>
        )}
      </CardContent>
      <CardFooter>
        {feedback ? (
          <Button onClick={onNext}>
            {feedback.state.session_complete ? 'See results' : 'Next question'}
          </Button>
        ) : (
          <Button
            disabled={selected.length === 0 || isSubmitting}
            onClick={() => onSubmit(question)}
          >
            {isSubmitting ? 'Submitting…' : 'Submit answer'}
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}

function AnswerInput({
  question,
  selected,
  onChange,
  disabled,
}: {
  question: SessionQuestion;
  selected: string[];
  onChange: (selected: string[]) => void;
  disabled: boolean;
}) {
  if (question.question_type === 'FillInBlank') {
    return (
      <Input
        value={selected[0] ?? ''}
        onChange={e => onChange(e.target.value ? [e.target.value] : [])}
        disabled={disabled}
        placeholder='Type your answer…'
      />
    );
  }

  const options =
    question.question_type === 'TrueFalse'
      ? ['True', 'False']
      : (question.options ?? []);
  const multi = question.question_type === 'MCQMultiSelect';

  function toggle(option: string) {
    if (disabled) return;
    onChange(
      multi
        ? selected.includes(option)
          ? selected.filter(o => o !== option)
          : [...selected, option]
        : [option]
    );
  }

  return (
    <div className='flex flex-col gap-2'>
      {options.map(option => (
        <Button
          key={option}
          type='button'
          variant={selected.includes(option) ? 'default' : 'outline'}
          disabled={disabled}
          className='justify-start'
          onClick={() => toggle(option)}
        >
          {option}
        </Button>
      ))}
    </div>
  );
}
