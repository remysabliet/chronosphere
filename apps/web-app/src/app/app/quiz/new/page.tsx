import { ListChecks } from 'lucide-react';
import Link from 'next/link';

import { ROUTES } from '@/lib/constants';
import { WizardAvatar } from '@/shared/components/wizard/wizard-avatar';
import { Card, CardDescription, CardHeader, CardTitle } from '@/ui/card';

export default function QuizNewPage() {
  return (
    <div className='mx-auto max-w-2xl space-y-6'>
      <h1 className='text-2xl font-bold'>Create a quiz</h1>
      <p className='text-muted-foreground'>How do you want to build it?</p>

      <div className='grid gap-4 sm:grid-cols-2'>
        <Link href={ROUTES.QUIZ_NEW_WIZARD}>
          <Card className='h-full transition-colors hover:bg-accent'>
            <CardHeader>
              <div className='mb-2'>
                <WizardAvatar size='md' />
              </div>
              <CardTitle>Build with the Wizard</CardTitle>
              <CardDescription>
                Tell the wizard what you want to learn, in your own words.
                It&apos;ll figure out the topic and check with you before
                generating questions.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link href={ROUTES.QUIZ_NEW_MANUAL}>
          <Card className='h-full transition-colors hover:bg-accent'>
            <CardHeader>
              <ListChecks className='mb-2 size-8 text-primary' />
              <CardTitle>Create manually</CardTitle>
              <CardDescription>
                Choose the question types and write the options yourself.
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
      </div>
    </div>
  );
}
