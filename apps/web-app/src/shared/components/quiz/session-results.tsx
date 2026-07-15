'use client';

import { CheckCircle2, ChevronDown, MinusCircle, XCircle } from 'lucide-react';
import Link from 'next/link';
import * as React from 'react';

import { ROUTES } from '@/lib/constants';
import { cn } from '@/lib/utils';
import {
  QuizDeletedBadge,
  sessionQuizLabel,
} from '@/shared/components/quiz/session-history';
import {
  scoreColorClass,
  type SessionReview,
  type SessionReviewEntry,
} from '@/types/session';
import { Button } from '@/ui/button';
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/ui/card';

function formatDuration(totalSeconds: number | null): string | null {
  if (totalSeconds === null) return null;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

function ScoreGauge({ percent }: { percent: number }) {
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, percent));

  return (
    <div className={cn('relative size-36', scoreColorClass(clamped))}>
      <svg viewBox='0 0 144 144' className='size-full -rotate-90'>
        <circle
          cx='72'
          cy='72'
          r={radius}
          fill='none'
          strokeWidth='12'
          className='stroke-muted'
        />
        <circle
          cx='72'
          cy='72'
          r={radius}
          fill='none'
          strokeWidth='12'
          strokeLinecap='round'
          stroke='currentColor'
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - clamped / 100)}
          className='transition-[stroke-dashoffset] duration-700'
        />
      </svg>
      <span className='absolute inset-0 flex items-center justify-center text-3xl font-bold'>
        {clamped}%
      </span>
    </div>
  );
}

function ReviewEntry({
  entry,
  index,
  reveal,
}: {
  entry: SessionReviewEntry;
  index: number;
  reveal: boolean;
}) {
  const [open, setOpen] = React.useState(false);
  const expandable = reveal || entry.selected.length > 0;
  const ungraded = entry.is_correct === null;

  return (
    <div
      className={cn(
        'rounded-lg border',
        ungraded
          ? 'border-border bg-muted/30'
          : entry.is_correct
            ? 'border-green-500/30 bg-green-500/5'
            : 'border-destructive/30 bg-destructive/5'
      )}
    >
      <button
        type='button'
        onClick={() => expandable && setOpen(prev => !prev)}
        className='flex w-full items-start gap-2 p-3 text-left'
      >
        {ungraded ? (
          <MinusCircle className='mt-0.5 size-4 shrink-0 text-muted-foreground' />
        ) : entry.is_correct ? (
          <CheckCircle2 className='mt-0.5 size-4 shrink-0 text-green-600 dark:text-green-400' />
        ) : (
          <XCircle className='mt-0.5 size-4 shrink-0 text-destructive' />
        )}
        <span className='flex-1 text-sm font-medium'>
          {index + 1}. {entry.question_text}
        </span>
        {ungraded && (
          <span className='mt-0.5 shrink-0 text-xs text-muted-foreground'>
            Not graded
          </span>
        )}
        {expandable && (
          <ChevronDown
            className={cn(
              'mt-0.5 size-4 shrink-0 text-muted-foreground transition-transform',
              open && 'rotate-180'
            )}
          />
        )}
      </button>
      {open && (
        <div className='space-y-2 border-t px-3 py-3 pl-9 text-sm'>
          <p
            className={cn(
              'font-medium',
              ungraded
                ? 'text-muted-foreground'
                : entry.is_correct
                  ? 'text-green-700 dark:text-green-400'
                  : 'text-destructive'
            )}
          >
            Your answer: {entry.selected.join(', ') || '—'}
          </p>
          {entry.correct_answers !== null && (
            <p className='text-green-700 dark:text-green-400'>
              Expected answer: {entry.correct_answers.join(', ')}
            </p>
          )}
          {reveal && entry.explanation && (
            <p className='text-muted-foreground'>{entry.explanation}</p>
          )}
        </div>
      )}
    </div>
  );
}

export function SessionResults({ review }: { review: SessionReview }) {
  const { summary, entries, feedback_mode } = review;
  const percent = Math.round(summary.accuracy * 100);
  const duration = formatDuration(summary.total_time_seconds);
  const reveal = feedback_mode !== 'never';
  const quizLabel = summary.quiz_title ?? summary.thema;
  const canRetake = summary.quiz_id !== null && !summary.quiz_deleted;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Quiz complete!</CardTitle>
        {quizLabel && (
          <p className='flex flex-wrap items-center gap-2 text-sm text-muted-foreground'>
            {sessionQuizLabel(summary)}
            {summary.quiz_deleted && <QuizDeletedBadge />}
          </p>
        )}
      </CardHeader>
      <CardContent className='space-y-6'>
        <div className='flex flex-col items-center gap-2'>
          <ScoreGauge percent={percent} />
          <p className='text-muted-foreground'>
            {summary.correct_answers} of {summary.total_questions} correct
            {duration ? ` · ${duration}` : ''}
          </p>
          {!reveal && (
            <p className='text-xs text-muted-foreground'>
              Exam mode — expected answers stay hidden.
            </p>
          )}
        </div>
        {entries.length > 0 && (
          <div className='space-y-2'>
            <p className='text-xs font-medium uppercase tracking-wide text-muted-foreground'>
              Your answers
            </p>
            {entries.map((entry, index) => (
              <ReviewEntry
                key={entry.question_id}
                entry={entry}
                index={index}
                reveal={reveal}
              />
            ))}
          </div>
        )}
      </CardContent>
      <CardFooter className='gap-2'>
        {canRetake && summary.quiz_id !== null && (
          <Button asChild>
            <Link href={ROUTES.QUIZ_DETAIL(summary.quiz_id)}>Retake quiz</Link>
          </Button>
        )}
        <Button asChild variant={canRetake ? 'outline' : 'default'}>
          <Link href={ROUTES.QUIZZES}>Back to quizzes</Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
