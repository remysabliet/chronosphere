import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { deleteQuizAction } from '@/lib/actions/quiz-actions';
import { toFriendlyErrorMessage } from '@/lib/errors';

/** Deletes a quiz and evicts it from the ['quiz', id] / ['quizzes', ...] query caches. */
export function useDeleteQuiz(onDeleted?: (quizId: string) => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (quizId: string) => deleteQuizAction(quizId),
    onSuccess: (_data, quizId) => {
      queryClient.removeQueries({ queryKey: ['quiz', quizId] });
      queryClient.invalidateQueries({ queryKey: ['quizzes'] });
      onDeleted?.(quizId);
    },
    onError: error => toast.error(toFriendlyErrorMessage(error)),
  });
}
