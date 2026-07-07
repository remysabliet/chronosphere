// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import * as React from 'react';
import { describe, it, vi } from 'vitest';

const confirmThemaAction = vi.fn();
const mapConceptsAction = vi.fn();
const generateQuestionsAction = vi.fn();

vi.mock('@/lib/actions/thema-actions', () => ({
  extractThemaAction: vi.fn(async () => ({
    status: 'resolved',
    extraction_id: 'ext-1',
    thema: 'JavaScript',
    domain: 'Software',
    topics: ['Closures', 'Promises'],
    confidence: 0.95,
    confirmation: "You'll be quizzed on JavaScript.",
    alternates: [],
    exposure_required: false,
  })),
  confirmThemaAction: (...args: unknown[]) => confirmThemaAction(...args),
  refineThemaAction: vi.fn(),
  submitExposureAction: vi.fn(async () => ({
    thema: 'JavaScript',
    exposure_level: 'Unseen',
    p_l0: 0.2,
    concepts_initialized: 2,
  })),
  interpretQuizLengthAction: vi.fn(),
  mapConceptsAction: (...args: unknown[]) => mapConceptsAction(...args),
  generateQuestionsAction: (...args: unknown[]) =>
    generateQuestionsAction(...args),
}));

vi.mock('next/link', () => ({
  default: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
}));

vi.mock('sonner', () => ({ toast: { error: vi.fn() } }));

import QuizWizardPage from '@/app/app/quiz/new/wizard/page';

// jsdom doesn't implement scrollIntoView — the wizard calls it on every
// message update purely for UX (auto-scroll), unrelated to what's tested here.
Element.prototype.scrollIntoView = vi.fn();

function renderWizard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <QuizWizardPage />
    </QueryClientProvider>
  );
}

const CONFIRMED_BASE = {
  status: 'resolved' as const,
  extraction_id: 'ext-1',
  thema: 'JavaScript',
  domain: 'Software',
  topics: ['Closures', 'Promises'],
  confidence: 0.95,
  confirmation: "You'll be quizzed on JavaScript.",
  alternates: [],
};

describe('wizard flow: confirm -> next step', () => {
  it('shows the quiz-length picker after confirming a thema with exposure already on file', async () => {
    confirmThemaAction.mockResolvedValue({
      ...CONFIRMED_BASE,
      exposure_required: false,
    });
    const user = userEvent.setup();
    renderWizard();

    const input = screen.getByLabelText('Message');
    await user.type(input, 'javascript closures');
    await user.keyboard('{Enter}');

    const confirmButton = await screen.findByText("Yes, that's right");
    await user.click(confirmButton);

    // findByText/getByText throw if the element isn't found, so reaching
    // these lines without throwing is itself the assertion.
    await screen.findByText(
      'How do you want to size the quiz?',
      {},
      { timeout: 3000 }
    );
    screen.getByText('Limit by number of questions');
    screen.getByText('Limit by time');
  });

  it('shows the exposure prompt after confirming a thema with no exposure on file', async () => {
    confirmThemaAction.mockResolvedValue({
      ...CONFIRMED_BASE,
      exposure_required: true,
    });
    const user = userEvent.setup();
    renderWizard();

    const input = screen.getByLabelText('Message');
    await user.type(input, 'javascript closures');
    await user.keyboard('{Enter}');

    const confirmButton = await screen.findByText("Yes, that's right");
    await user.click(confirmButton);

    await screen.findByText(
      'How familiar are you with this already?',
      {},
      { timeout: 3000 }
    );
    const exposureOption = screen.getByText('Never heard of it');
    await user.click(exposureOption);

    await screen.findByText(
      'How do you want to size the quiz?',
      {},
      { timeout: 3000 }
    );
  });

  it('actually calls mapConceptsAction/generateQuestionsAction after quiz length + question types are both answered', async () => {
    confirmThemaAction.mockResolvedValue({
      ...CONFIRMED_BASE,
      exposure_required: false,
    });
    mapConceptsAction.mockResolvedValue({
      thema: 'JavaScript',
      concepts: [
        {
          id: 'concept-1',
          topic: 'Closures',
          concept: 'Lexical scope',
          learning_goal: 'Understand closures',
          bloom_levels: ['Remembering'],
          estimated_time_minutes: 10,
          complexity_level: 'Medium',
        },
      ],
    });
    generateQuestionsAction.mockResolvedValue({
      concept_id: 'concept-1',
      bloom_level: 'Remembering',
      difficulty_tier: 'medium',
      questions: [{ id: 'q-1' }],
    });

    const user = userEvent.setup();
    renderWizard();

    const input = screen.getByLabelText('Message');
    await user.type(input, 'javascript closures');
    await user.keyboard('{Enter}');

    const confirmButton = await screen.findByText("Yes, that's right");
    await user.click(confirmButton);

    await screen.findByText(
      'How do you want to size the quiz?',
      {},
      { timeout: 3000 }
    );
    // Leave both toggles off (fully unlimited) and continue — only one
    // "Continue" button exists at this point (question types hasn't shown yet).
    await user.click(screen.getByText('Continue'));

    await screen.findByText(
      'What kind of questions do you want? Pick one or more.',
      {},
      { timeout: 3000 }
    );
    await user.click(screen.getByText('Multiple choice (one answer)'));
    await user.click(screen.getByText('Continue'));

    await screen.findByText(
      /question.*ready|no questions made it through/i,
      {},
      { timeout: 5000 }
    );

    if (mapConceptsAction.mock.calls.length === 0) {
      throw new Error(
        'mapConceptsAction was never called — the generateMutation effect did not fire.'
      );
    }
    if (generateQuestionsAction.mock.calls.length === 0) {
      throw new Error('generateQuestionsAction was never called.');
    }
  });
});
