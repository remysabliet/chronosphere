'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BookmarkPlus, Check, Pencil, Trash2, X } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { toast } from 'sonner';

import { useCopyQuiz } from '@/hooks/use-copy-quiz';
import { useDeleteQuiz } from '@/hooks/use-delete-quiz';
import { useQuizEvents } from '@/hooks/use-quiz-events';
import { useQuizProgress } from '@/hooks/use-quiz-progress';
import { renameQuizAction } from '@/lib/actions/quiz-actions';
import {
  getSessionPreferencesAction,
  startSessionAction,
} from '@/lib/actions/session-actions';
import { ROUTES } from '@/lib/constants';
import { isSessionExpiredError, toFriendlyErrorMessage } from '@/lib/errors';
import { cn, formatDate } from '@/lib/utils';
import { SessionExpiredDialog } from '@/shared/components/auth/session-expired-dialog';
import { DeleteQuizDialog } from '@/shared/components/quiz/delete-quiz-dialog';
import { SessionHistoryCard } from '@/shared/components/quiz/session-history';
import { quizProgressPercent, type QuizDetailResponse } from '@/types/quiz';
import { FEEDBACK_MODES, type FeedbackMode } from '@/types/session';
import { Button } from '@/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card';
import { Input } from '@/ui/input';
import * as React from 'react';

function QuizTitle({
  quiz,
  quizId,
}: {
  quiz: QuizDetailResponse;
  quizId: string;
}) {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = React.useState(false);
  const [draft, setDraft] = React.useState(quiz.title);

  const renameMutation = useMutation({
    mutationFn: (title: string) => renameQuizAction(quizId, title),
    onSuccess: updated => {
      queryClient.setQueryData(['quiz', quizId], updated);
      queryClient.invalidateQueries({ queryKey: ['quizzes'] });
      setIsEditing(false);
    },
    onError: error => toast.error(toFriendlyErrorMessage(error)),
  });

  function startEditing() {
    setDraft(quiz.title);
    setIsEditing(true);
  }

  function submit() {
    const title = draft.trim();
    if (!title || title === quiz.title) {
      setIsEditing(false);
      return;
    }
    renameMutation.mutate(title);
  }

  if (isEditing) {
    return (
      <div className='flex items-center gap-2'>
        <Input
          autoFocus
          value={draft}
          maxLength={200}
          disabled={renameMutation.isPending}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') submit();
            if (e.key === 'Escape') setIsEditing(false);
          }}
          className='text-2xl font-bold'
        />
        <Button
          size='icon'
          variant='ghost'
          disabled={renameMutation.isPending}
          onClick={submit}
        >
          <Check className='size-4' />
        </Button>
        <Button size='icon' variant='ghost' onClick={() => setIsEditing(false)}>
          <X className='size-4' />
        </Button>
      </div>
    );
  }

  return (
    <div className='group flex items-center gap-2'>
      <h1 className='text-2xl font-bold'>{quiz.title}</h1>
      {quiz.is_owner && (
        <Button
          size='icon'
          variant='ghost'
          className='opacity-0 group-hover:opacity-100'
          onClick={startEditing}
        >
          <Pencil className='size-4' />
        </Button>
      )}
    </div>
  );
}

export default function QuizDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  // Live generation progress: SSE events patch the query cache in place.
  useQuizEvents();
  const { data: quiz, isLoading, isError } = useQuizProgress(params.id);
  const [sessionExpired, setSessionExpired] = React.useState(false);
  const deleteQuiz = useDeleteQuiz(() => router.push(ROUTES.QUIZZES));
  const copyQuiz = useCopyQuiz(copy =>
    router.push(ROUTES.QUIZ_DETAIL(copy.id))
  );

  const preferencesQuery = useQuery({
    queryKey: ['session-preferences'],
    queryFn: getSessionPreferencesAction,
  });
  const [feedbackMode, setFeedbackMode] = React.useState<FeedbackMode | null>(
    null
  );
  const selectedMode =
    feedbackMode ?? preferencesQuery.data?.default_feedback_mode ?? 'end';

  const startMutation = useMutation({
    mutationFn: () => startSessionAction(params.id, feedbackMode),
    onSuccess: state => router.push(ROUTES.SESSION(state.session_id)),
    onError: error => {
      if (isSessionExpiredError(error)) {
        setSessionExpired(true);
        return;
      }
      toast.error(toFriendlyErrorMessage(error));
    },
  });

  if (isLoading) {
    return <p className='text-muted-foreground'>Loading…</p>;
  }

  if (isError || !quiz) {
    return <p className='text-muted-foreground'>Quiz not found.</p>;
  }

  const percent = quizProgressPercent(quiz);

  return (
    <div className='mx-auto max-w-2xl space-y-6'>
      <SessionExpiredDialog open={sessionExpired} />
      <div className='flex flex-wrap items-center justify-between gap-4'>
        <div className='space-y-1'>
          <QuizTitle quiz={quiz} quizId={params.id} />
          <p className='text-muted-foreground'>{quiz.thema}</p>
          {quiz.topics.length > 0 && (
            <div className='flex flex-wrap gap-1.5'>
              {quiz.topics.map(topic => (
                <span
                  key={topic}
                  className='rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground'
                >
                  {topic}
                </span>
              ))}
            </div>
          )}
          <p className='text-xs text-muted-foreground'>
            Created {formatDate(quiz.created_at)}
          </p>
        </div>
        <div className='flex items-center gap-2'>
          {quiz.is_owner ? (
            <DeleteQuizDialog
              quizTitle={quiz.title}
              onConfirm={() => deleteQuiz.mutate(params.id)}
              trigger={
                <Button
                  type='button'
                  variant='ghost'
                  size='icon'
                  aria-label='Delete quiz'
                  className='text-muted-foreground hover:text-destructive'
                >
                  <Trash2 className='size-4' />
                </Button>
              }
            />
          ) : (
            <Button
              type='button'
              variant='outline'
              disabled={copyQuiz.isPending}
              onClick={() => copyQuiz.mutate(params.id)}
            >
              <BookmarkPlus className='size-4' />
              {copyQuiz.isPending ? 'Saving…' : 'Save to my quizzes'}
            </Button>
          )}
          <Button
            disabled={
              quiz.questions_ready === 0 ||
              preferencesQuery.isPending ||
              startMutation.isPending
            }
            onClick={() => startMutation.mutate()}
          >
            {startMutation.isPending ? 'Starting…' : 'Start quiz'}
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className='text-base'>Feedback</CardTitle>
        </CardHeader>
        <CardContent>
          <div className='grid gap-2 sm:grid-cols-3'>
            {FEEDBACK_MODES.map(mode => (
              <button
                key={mode.value}
                type='button'
                onClick={() => setFeedbackMode(mode.value)}
                className={cn(
                  'rounded-lg border p-3 text-left transition-colors',
                  selectedMode === mode.value
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:bg-muted/50'
                )}
              >
                <p className='text-sm font-medium'>{mode.label}</p>
                <p className='mt-0.5 text-xs text-muted-foreground'>
                  {mode.description}
                </p>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className='text-base'>Configuration</CardTitle>
        </CardHeader>
        <CardContent className='space-y-1 text-sm text-muted-foreground'>
          <p>
            {quiz.question_count !== null
              ? `${quiz.question_count} questions`
              : 'No fixed question count'}
          </p>
          <p>
            {quiz.time_limit_minutes !== null
              ? `${quiz.time_limit_minutes} minute limit`
              : 'No time limit'}
          </p>
          <p>{quiz.question_types.join(', ')}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className='text-base'>
            {quiz.status === 'ready'
              ? 'Ready to go'
              : `Generating your questions… ${percent}%`}
          </CardTitle>
        </CardHeader>
        <CardContent className='space-y-2'>
          <div className='h-2 w-full overflow-hidden rounded-full bg-muted'>
            <div
              className='h-full rounded-full bg-primary transition-all'
              style={{ width: `${percent}%` }}
            />
          </div>
          {quiz.questions_ready > 0 && (
            <p className='text-xs text-muted-foreground'>
              {quiz.questions_ready} question
              {quiz.questions_ready === 1 ? '' : 's'} ready
            </p>
          )}
        </CardContent>
      </Card>

      <SessionHistoryCard quizId={params.id} />
    </div>
  );
}
