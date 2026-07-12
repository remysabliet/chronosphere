import { useQuery } from '@tanstack/react-query';

import { getQuizAction } from '@/lib/actions/quiz-actions';

const POLL_INTERVAL_MS = 3000;

/**
 * Short-polls a quiz's generation progress. Stops refetching once the quiz
 * is ready — see docs/product/ui-update-plan.md §3 for why polling (not SSE)
 * is the right transport at today's event rate (~1 batch / 10-30s).
 */
export function useQuizProgress(quizId: string) {
  return useQuery({
    queryKey: ['quiz', quizId],
    queryFn: () => getQuizAction(quizId),
    refetchInterval: query =>
      query.state.data?.status === 'ready' ? false : POLL_INTERVAL_MS,
  });
}
