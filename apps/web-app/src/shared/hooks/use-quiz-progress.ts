import { useQuery } from '@tanstack/react-query';

import { getQuizAction } from '@/lib/actions/quiz-actions';

/**
 * Reads a quiz's detail, including generation progress. Live updates arrive
 * over SSE (useQuizEvents patches this query's cache in place), so no
 * polling here — see docs/product/ui-update-plan.md §3.
 */
export function useQuizProgress(quizId: string) {
  return useQuery({
    queryKey: ['quiz', quizId],
    queryFn: () => getQuizAction(quizId),
  });
}
