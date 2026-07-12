import { Globe, Loader2 } from 'lucide-react';
import Link from 'next/link';

import { ROUTES } from '@/lib/constants';
import type { QuestionType } from '@/types/thema';
import { quizProgressPercent, type QuizListItem } from '@/types/quiz';
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/ui/card';
import { buttonVariants } from '@/ui/button';
import { cn, formatDate } from '@/lib/utils';

const MAX_VISIBLE_TOPICS = 3;

const TYPE_INITIALS: Record<QuestionType, string> = {
  MCQ: 'MCQ',
  MCQMultiSelect: 'MCQ+',
  TrueFalse: 'T/F',
  FillInBlank: 'Fill',
};

function questionCountLabel(item: QuizListItem): string {
  return item.question_count !== null
    ? `${item.question_count} questions`
    : `~${item.questions_expected} questions`;
}

function timeLimitLabel(item: QuizListItem): string {
  return item.time_limit_minutes !== null
    ? `${item.time_limit_minutes} min`
    : 'No limit';
}

export function QuizCard({
  item,
  showOwner = false,
}: {
  item: QuizListItem;
  showOwner?: boolean;
}) {
  const generating = item.status === 'generating';
  const percent = quizProgressPercent(item);

  return (
    <Link href={ROUTES.QUIZ_DETAIL(item.id)} className='block h-full'>
      <Card className='flex h-full flex-col transition-colors hover:bg-accent'>
        <CardHeader className='space-y-1'>
          <CardTitle className='text-lg'>{item.title}</CardTitle>
          <p className='text-sm text-muted-foreground'>{item.thema}</p>
        </CardHeader>
        <CardContent className='flex-1 space-y-2'>
          {item.topics.length > 0 && (
            <div className='flex flex-wrap gap-1.5'>
              {item.topics.slice(0, MAX_VISIBLE_TOPICS).map(topic => (
                <span
                  key={topic}
                  className='rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground'
                >
                  {topic}
                </span>
              ))}
              {item.topics.length > MAX_VISIBLE_TOPICS && (
                <span className='rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground'>
                  +{item.topics.length - MAX_VISIBLE_TOPICS}
                </span>
              )}
            </div>
          )}
          <p className='text-xs text-muted-foreground'>
            {questionCountLabel(item)} · {timeLimitLabel(item)} ·{' '}
            {item.question_types.map(type => TYPE_INITIALS[type]).join(', ')}
          </p>
          {showOwner && item.owner_name && (
            <p className='flex items-center gap-1.5 text-xs text-muted-foreground'>
              <Globe className='size-3.5' />
              {item.owner_name}
            </p>
          )}
          {generating && (
            <p className='flex items-center gap-1.5 text-xs text-primary'>
              <Loader2 className='size-3.5 animate-spin' />
              Generating… {percent}%
            </p>
          )}
          <p className='text-xs text-muted-foreground'>
            Created {formatDate(item.created_at, { month: 'short' })}
          </p>
        </CardContent>
        <CardFooter>
          <span
            className={cn(
              buttonVariants({ size: 'sm' }),
              'w-full',
              generating && 'pointer-events-none opacity-50'
            )}
          >
            {generating ? 'Generating…' : 'Start'}
          </span>
        </CardFooter>
      </Card>
    </Link>
  );
}
