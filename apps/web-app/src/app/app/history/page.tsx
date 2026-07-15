'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import * as React from 'react';

import { listSessionsAction } from '@/lib/actions/session-actions';
import { ROUTES } from '@/lib/constants';
import { cn, formatDate } from '@/lib/utils';
import { SegmentedControl } from '@/shared/components/quiz/segmented-control';
import {
  HistoryRow,
  QuizDeletedBadge,
  sessionQuizLabel,
} from '@/shared/components/quiz/session-history';
import { scoreColorClass, type SessionHistoryEntry } from '@/types/session';
import { Button } from '@/ui/button';

type HistoryView = 'date' | 'quiz';

const VIEW_OPTIONS = [
  { value: 'date', label: 'By date' },
  { value: 'quiz', label: 'By quiz' },
] as const;

const DAY_MS = 86_400_000;

function dayLabel(iso: string): string {
  const date = new Date(iso);
  const startOfDay = (d: Date) =>
    new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const daysAgo = Math.round(
    (startOfDay(new Date()) - startOfDay(date)) / DAY_MS
  );
  if (daysAgo === 0) return 'Today';
  if (daysAgo === 1) return 'Yesterday';
  return formatDate(iso);
}

function groupBy<T>(
  items: readonly T[],
  key: (item: T) => string
): [string, T[]][] {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const groupKey = key(item);
    const existing = groups.get(groupKey);
    if (existing) {
      existing.push(item);
    } else {
      groups.set(groupKey, [item]);
    }
  }
  return [...groups.entries()];
}

function DateGroups({ sessions }: { sessions: SessionHistoryEntry[] }) {
  const groups = groupBy(sessions, entry => dayLabel(entry.started_at));

  return (
    <div className='space-y-6'>
      {groups.map(([label, entries]) => (
        <section key={label} className='space-y-2'>
          <h2 className='text-xs font-medium uppercase tracking-wide text-muted-foreground'>
            {label}
          </h2>
          {entries.map(entry => (
            <HistoryRow key={entry.session_id} entry={entry} showQuiz />
          ))}
        </section>
      ))}
    </div>
  );
}

function bestScore(entries: SessionHistoryEntry[]): number | null {
  const completed = entries.filter(entry => entry.status === 'completed');
  if (completed.length === 0) return null;
  return Math.round(Math.max(...completed.map(entry => entry.accuracy)) * 100);
}

function QuizGroups({ sessions }: { sessions: SessionHistoryEntry[] }) {
  const groups = groupBy(
    sessions,
    entry => entry.quiz_id ?? `session:${entry.session_id}`
  );

  return (
    <div className='space-y-6'>
      {groups.map(([key, entries]) => {
        const first = entries[0];
        if (first === undefined) return null;
        const best = bestScore(entries);
        const retakeable = first.quiz_id !== null && !first.quiz_deleted;

        return (
          <section key={key} className='space-y-2'>
            <div className='flex flex-wrap items-center gap-2'>
              {retakeable && first.quiz_id !== null ? (
                <Link
                  href={ROUTES.QUIZ_DETAIL(first.quiz_id)}
                  className='text-sm font-semibold hover:underline'
                >
                  {sessionQuizLabel(first)}
                </Link>
              ) : (
                <span className='text-sm font-semibold'>
                  {sessionQuizLabel(first)}
                </span>
              )}
              {first.quiz_deleted && <QuizDeletedBadge />}
              <span className='text-xs text-muted-foreground'>
                {entries.length} attempt{entries.length === 1 ? '' : 's'}
                {best !== null && (
                  <>
                    {' · best '}
                    <span className={cn('font-medium', scoreColorClass(best))}>
                      {best}%
                    </span>
                  </>
                )}
              </span>
            </div>
            {entries.map(entry => (
              <HistoryRow key={entry.session_id} entry={entry} />
            ))}
          </section>
        );
      })}
    </div>
  );
}

export default function HistoryPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['session-history'],
    queryFn: () => listSessionsAction(),
  });
  const [view, setView] = React.useState<HistoryView>('date');

  const sessions = data?.sessions ?? [];

  return (
    <div className='mx-auto max-w-2xl space-y-6'>
      <div className='flex flex-wrap items-center justify-between gap-4'>
        <div>
          <h1 className='text-2xl font-bold'>History</h1>
          <p className='text-sm text-muted-foreground'>
            Every quiz session you&apos;ve taken — even when the quiz itself is
            gone.
          </p>
        </div>
        <SegmentedControl
          options={VIEW_OPTIONS}
          value={view}
          onChange={setView}
        />
      </div>

      {isLoading ? (
        <p className='text-muted-foreground'>Loading…</p>
      ) : isError ? (
        <p className='text-muted-foreground'>
          Your history couldn&apos;t be loaded.
        </p>
      ) : sessions.length === 0 ? (
        <div className='rounded-lg border border-dashed p-10 text-center'>
          <p className='font-medium'>No sessions yet</p>
          <p className='mt-1 text-sm text-muted-foreground'>
            Take a quiz and your results will show up here.
          </p>
          <Button asChild className='mt-4'>
            <Link href={ROUTES.QUIZZES}>Browse quizzes</Link>
          </Button>
        </div>
      ) : view === 'date' ? (
        <DateGroups sessions={sessions} />
      ) : (
        <QuizGroups sessions={sessions} />
      )}
    </div>
  );
}
