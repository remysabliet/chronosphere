import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { copyQuizAction } from '@/lib/actions/quiz-actions';
import { toFriendlyErrorMessage } from '@/lib/errors';
import type { QuizDetailResponse } from '@/types/quiz';

/** Saves a shared quiz as the user's own copy and refreshes the quiz lists. */
export function useCopyQuiz(onCopied?: (copy: QuizDetailResponse) => void) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (quizId: string) => copyQuizAction(quizId),
    onSuccess: copy => {
      queryClient.setQueryData(['quiz', copy.id], copy);
      queryClient.invalidateQueries({ queryKey: ['quizzes'] });
      toast.success('Saved to your quizzes');
      onCopied?.(copy);
    },
    onError: error => toast.error(toFriendlyErrorMessage(error)),
  });
}
