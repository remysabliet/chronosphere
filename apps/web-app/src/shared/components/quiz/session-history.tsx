'use client';

import { useQuery } from '@tanstack/react-query';
import { Archive, ChevronRight } from 'lucide-react';
import Link from 'next/link';

import { listSessionsAction } from '@/lib/actions/session-actions';
import { ROUTES } from '@/lib/constants';
import { cn, formatDate } from '@/lib/utils';
import {
  FEEDBACK_MODES,
  scoreColorClass,
  type SessionHistoryEntry,
} from '@/types/session';
import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card';

function modeLabel(entry: SessionHistoryEntry): string {
  return (
    FEEDBACK_MODES.find(mode => mode.value === entry.feedback_mode)?.label ??
    entry.feedback_mode
  );
}

export function sessionQuizLabel(entry: {
  quiz_title: string | null;
  thema: string | null;
}): string {
  return entry.quiz_title ?? entry.thema ?? 'Untitled quiz';
}

export function QuizDeletedBadge({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground',
        className
      )}
    >
      <Archive className='size-3' />
      Quiz deleted
    </span>
  );
}

export function HistoryRow({
  entry,
  showQuiz = false,
}: {
  entry: SessionHistoryEntry;
  showQuiz?: boolean;
}) {
  const percent = Math.round(entry.accuracy * 100);
  const completed = entry.status === 'completed';
  const outcome = completed
    ? `${entry.correct_answers} of ${entry.total_questions} correct`
    : 'In progress';

  return (
    <Link
      href={ROUTES.SESSION(entry.session_id)}
      className='flex items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-muted/50'
    >
      <span
        className={cn(
          'w-12 text-right text-lg font-bold tabular-nums',
          completed ? scoreColorClass(percent) : 'text-muted-foreground'
        )}
      >
        {completed ? `${percent}%` : '—'}
      </span>
      <span className='flex-1 text-sm'>
        {showQuiz ? (
          <span className='flex flex-wrap items-center gap-2 font-medium'>
            {sessionQuizLabel(entry)}
            {entry.quiz_deleted && <QuizDeletedBadge />}
          </span>
        ) : (
          <span className='font-medium'>{outcome}</span>
        )}
        <span className='block text-xs text-muted-foreground'>
          {showQuiz ? `${outcome} · ` : ''}
          {formatDate(entry.started_at)} · {modeLabel(entry)}
        </span>
      </span>
      <span className='text-xs text-muted-foreground'>
        {completed ? 'View results' : 'Resume'}
      </span>
      <ChevronRight className='size-4 shrink-0 text-muted-foreground' />
    </Link>
  );
}

export function SessionHistoryCard({ quizId }: { quizId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['session-history', quizId],
    queryFn: () => listSessionsAction(quizId),
  });

  const sessions = data?.sessions ?? [];
  if (!isLoading && sessions.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className='text-base'>Previous sessions</CardTitle>
      </CardHeader>
      <CardContent className='space-y-2'>
        {isLoading ? (
          <p className='text-sm text-muted-foreground'>Loading…</p>
        ) : (
          sessions.map(entry => (
            <HistoryRow key={entry.session_id} entry={entry} />
          ))
        )}
      </CardContent>
    </Card>
  );
}
