'use client';

import { useInfiniteQuery } from '@tanstack/react-query';
import { PlusCircle, Search } from 'lucide-react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import * as React from 'react';

import { useDebouncedValue } from '@/hooks/use-debounced-value';
import { useQuizEvents } from '@/hooks/use-quiz-events';
import { listQuizzesAction } from '@/lib/actions/quiz-actions';
import { ROUTES, TIMEOUTS } from '@/lib/constants';
import { QuizCard } from '@/shared/components/quiz/quiz-card';
import {
  SegmentedControl,
  type SegmentedControlOption,
} from '@/shared/components/quiz/segmented-control';
import { WizardAvatar } from '@/shared/components/wizard/wizard-avatar';
import type { QuizScope, QuizStatus } from '@/types/quiz';
import { Button } from '@/ui/button';
import { Input } from '@/ui/input';

const VIEW_OPTIONS: readonly SegmentedControlOption<QuizScope>[] = [
  { value: 'mine', label: 'My quizzes' },
  { value: 'shared', label: 'Shared' },
];

const STATUS_CHIPS: readonly { value: QuizStatus; label: string }[] = [
  { value: 'ready', label: 'Ready' },
  { value: 'generating', label: 'Generating' },
];

export default function QuizLibraryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const view: QuizScope =
    searchParams.get('view') === 'shared' ? 'shared' : 'mine';

  const [query, setQuery] = React.useState('');
  const debouncedQuery = useDebouncedValue(query, TIMEOUTS.DEBOUNCE);
  const [status, setStatus] = React.useState<QuizStatus | null>(null);

  function setView(next: QuizScope) {
    const params = new URLSearchParams(searchParams);
    if (next === 'mine') params.delete('view');
    else params.set('view', next);
    router.replace(`${ROUTES.QUIZZES}?${params.toString()}`);
  }

  function clearFilters() {
    setQuery('');
    setStatus(null);
  }

  const hasFilters = debouncedQuery.length > 0 || status !== null;

  // Generation progress is pushed over SSE and patched into this query's
  // cache — no interval refetching.
  useQuizEvents();

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading } =
    useInfiniteQuery({
      queryKey: ['quizzes', view, debouncedQuery, status],
      queryFn: ({ pageParam }) =>
        listQuizzesAction({
          scope: view,
          q: debouncedQuery || undefined,
          status: status ?? undefined,
          page: pageParam,
        }),
      initialPageParam: 1,
      getNextPageParam: (lastPage, allPages) =>
        lastPage.has_more ? allPages.length + 1 : undefined,
    });

  const items = data?.pages.flatMap(page => page.items) ?? [];

  return (
    <div className='space-y-6'>
      <div className='flex flex-wrap items-center justify-between gap-4'>
        <h1 className='text-2xl font-bold'>Quizzes</h1>
        <Button asChild>
          <Link href={ROUTES.QUIZ_NEW}>
            <PlusCircle className='size-4' />
            New quiz
          </Link>
        </Button>
      </div>

      <div className='flex flex-wrap items-center gap-3'>
        <SegmentedControl
          options={VIEW_OPTIONS}
          value={view}
          onChange={setView}
        />

        <div className='relative min-w-[220px] flex-1'>
          <Search className='absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground' />
          <Input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder='Search by title, thema, or topic…'
            className='pl-9'
          />
        </div>

        {STATUS_CHIPS.map(chip => {
          const active = status === chip.value;
          return (
            <Button
              key={chip.value}
              type='button'
              size='sm'
              aria-pressed={active}
              variant={active ? 'default' : 'outline'}
              className='rounded-full'
              onClick={() =>
                setStatus(prev => (prev === chip.value ? null : chip.value))
              }
            >
              {chip.label}
            </Button>
          );
        })}
      </div>

      {!isLoading && items.length === 0 ? (
        <EmptyState
          view={view}
          hasFilters={hasFilters}
          onClearFilters={clearFilters}
        />
      ) : (
        <div className='grid gap-4 sm:grid-cols-2 lg:grid-cols-3'>
          {items.map(item => (
            <QuizCard key={item.id} item={item} />
          ))}
        </div>
      )}

      {hasNextPage && (
        <div className='flex justify-center'>
          <Button
            variant='outline'
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
          >
            {isFetchingNextPage ? 'Loading…' : 'Load more'}
          </Button>
        </div>
      )}
    </div>
  );
}

function EmptyState({
  view,
  hasFilters,
  onClearFilters,
}: {
  view: QuizScope;
  hasFilters: boolean;
  onClearFilters: () => void;
}) {
  if (hasFilters) {
    return (
      <div className='flex flex-col items-center gap-3 rounded-lg border border-dashed py-16 text-center'>
        <p className='text-muted-foreground'>No quizzes match</p>
        <Button variant='ghost' size='sm' onClick={onClearFilters}>
          Clear filters
        </Button>
      </div>
    );
  }

  if (view === 'shared') {
    return (
      <div className='flex flex-col items-center gap-3 rounded-lg border border-dashed py-16 text-center'>
        <p className='text-muted-foreground'>Nobody has shared a quiz yet…</p>
      </div>
    );
  }

  return (
    <div className='flex flex-col items-center gap-4 rounded-lg border border-dashed py-16 text-center'>
      <WizardAvatar size='md' />
      <p className='text-muted-foreground'>
        No quizzes yet — let&apos;s fix that.
      </p>
      <Button asChild>
        <Link href={ROUTES.QUIZ_NEW}>Create your first quiz</Link>
      </Button>
    </div>
  );
}
