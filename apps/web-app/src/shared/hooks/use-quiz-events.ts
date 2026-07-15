import {
  useQueryClient,
  type InfiniteData,
  type QueryClient,
} from '@tanstack/react-query';
import * as React from 'react';

import type {
  QuizDetailResponse,
  QuizListResponse,
  QuizProgress,
  QuizProgressEvent,
} from '@/types/quiz';

const QUIZ_EVENTS_URL = '/api/quiz-events';

function applyProgressEvent(
  queryClient: QueryClient,
  event: QuizProgressEvent
): void {
  const progress: QuizProgress = {
    questions_ready: event.questions_ready,
    questions_expected: event.questions_expected,
    jobs_completed: event.jobs_completed,
    jobs_total: event.jobs_total,
    status: event.status,
  };

  queryClient.setQueryData<QuizDetailResponse>(['quiz', event.quiz_id], old =>
    old ? { ...old, ...progress } : undefined
  );

  queryClient.setQueriesData<InfiniteData<QuizListResponse>>(
    { queryKey: ['quizzes'] },
    old =>
      old && {
        ...old,
        pages: old.pages.map(page => ({
          ...page,
          items: page.items.map(item =>
            item.id === event.quiz_id ? { ...item, ...progress } : item
          ),
        })),
      }
  );

  // In-place patches can't move a quiz in or out of a status-filtered list,
  // so completion also triggers one refetch — once per quiz, not per tick.
  if (event.status === 'ready') {
    void queryClient.invalidateQueries({ queryKey: ['quizzes'] });
  }
}

/**
 * Subscribes to the per-user quiz generation stream (SSE) and patches the
 * react-query caches in place — no polling. Mount once per page that shows
 * generation progress; EventSource reconnects on its own after drops, and a
 * reconnect refetches quiz queries to cover any events missed while offline.
 */
export function useQuizEvents(): void {
  const queryClient = useQueryClient();

  React.useEffect(() => {
    const source = new EventSource(QUIZ_EVENTS_URL);
    let droppedConnection = false;

    source.onmessage = message => {
      const event = JSON.parse(
        message.data as string
      ) as QuizProgressEvent | null;
      if (event) applyProgressEvent(queryClient, event);
    };
    source.onerror = () => {
      droppedConnection = true;
    };
    source.onopen = () => {
      if (!droppedConnection) return;
      droppedConnection = false;
      void queryClient.invalidateQueries({ queryKey: ['quizzes'] });
      void queryClient.invalidateQueries({ queryKey: ['quiz'] });
    };

    return () => source.close();
  }, [queryClient]);
}
