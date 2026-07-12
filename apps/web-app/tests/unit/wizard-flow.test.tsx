// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import * as React from 'react';
import { describe, it, vi } from 'vitest';

const confirmThemaAction = vi.fn();
const createQuizAction = vi.fn();
const refineThemaAction = vi.fn();

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
  refineThemaAction: (...args: unknown[]) => refineThemaAction(...args),
  submitExposureAction: vi.fn(async () => ({
    thema: 'JavaScript',
    exposure_level: 'Unseen',
    p_l0: 0.2,
    concepts_initialized: 2,
  })),
  interpretQuizLengthAction: vi.fn(),
}));

vi.mock('@/lib/actions/quiz-actions', () => ({
  createQuizAction: (...args: unknown[]) => createQuizAction(...args),
}));

vi.mock('next/link', () => ({
  default: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
}));

vi.mock('sonner', () => ({ toast: { error: vi.fn() } }));

import QuizWizardPage from '@/app/app/quiz/new/page';

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

function last(elements: HTMLElement[]): HTMLElement {
  const element = elements[elements.length - 1];
  if (!element) throw new Error('expected at least one element');
  return element;
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

  it('actually calls createQuizAction after quiz length + question types are both answered', async () => {
    confirmThemaAction.mockResolvedValue({
      ...CONFIRMED_BASE,
      exposure_required: false,
    });
    createQuizAction.mockResolvedValue({
      id: 'quiz-1',
      thema: 'JavaScript',
      title: 'JavaScript',
      question_types: ['MCQ'],
      question_count: 20,
      time_limit_minutes: null,
      visibility: 'private',
      generation_batches_enqueued: 4,
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
      /questions are being generated now/i,
      {},
      { timeout: 5000 }
    );

    if (createQuizAction.mock.calls.length === 0) {
      throw new Error(
        'createQuizAction was never called — the generateMutation effect did not fire.'
      );
    }
  });

  it('does not silently reuse stale size/type answers when refining after a quiz was already generated', async () => {
    // No global mock-clearing config in this suite — earlier tests' calls
    // otherwise leak into this test's call-count assertions.
    createQuizAction.mockClear();
    confirmThemaAction.mockReset();
    confirmThemaAction
      .mockResolvedValueOnce({ ...CONFIRMED_BASE, exposure_required: false })
      .mockResolvedValueOnce({
        ...CONFIRMED_BASE,
        extraction_id: 'ext-2',
        thema: 'Python',
        exposure_required: false,
      });
    refineThemaAction.mockResolvedValue({
      ...CONFIRMED_BASE,
      extraction_id: 'ext-2',
      thema: 'Python',
    });
    createQuizAction.mockResolvedValue({
      id: 'quiz-1',
      thema: 'JavaScript',
      title: 'JavaScript',
      question_types: ['MCQ'],
      question_count: 20,
      time_limit_minutes: null,
      visibility: 'private',
      generation_batches_enqueued: 4,
    });

    const user = userEvent.setup();
    renderWizard();

    const input = screen.getByLabelText('Message');
    await user.type(input, 'javascript closures');
    await user.keyboard('{Enter}');
    await user.click(await screen.findByText("Yes, that's right"));

    await screen.findByText(
      'How do you want to size the quiz?',
      {},
      { timeout: 3000 }
    );
    await user.click(screen.getByText('Continue'));
    await screen.findByText(
      'What kind of questions do you want? Pick one or more.',
      {},
      { timeout: 3000 }
    );
    await user.click(screen.getByText('Multiple choice (one answer)'));
    await user.click(screen.getByText('Continue'));
    await screen.findByText(
      /questions are being generated now/i,
      {},
      { timeout: 5000 }
    );

    // Keep chatting, as the UI itself invites ("Want something else covered?
    // Tell me below.") — this refines into a brand-new extraction_id. The
    // first round's "Yes, that's right" button is still in the transcript,
    // so wait for a second one to appear and click that (the newest).
    await user.type(input, 'python basics');
    await user.keyboard('{Enter}');
    await vi.waitFor(() => {
      if (screen.getAllByText("Yes, that's right").length < 2) {
        throw new Error('waiting for the second confirm button');
      }
    });
    await user.click(last(screen.getAllByText("Yes, that's right")));

    // Creating the second quiz must wait for the learner to actually answer
    // the new prompts — it must not fire automatically off stale answers.
    await screen.findAllByText(
      'How do you want to size the quiz?',
      {},
      { timeout: 3000 }
    );
    if (createQuizAction.mock.calls.length !== 1) {
      throw new Error(
        `Expected createQuizAction to still have been called exactly once ` +
          `pending the new answers, got ${createQuizAction.mock.calls.length}.`
      );
    }

    // The new size prompt must be genuinely answerable (not locked from the
    // previous round) — walk through it same as the first round.
    await user.click(last(screen.getAllByText('Continue')));

    await vi.waitFor(() => {
      if (
        screen.getAllByText(
          'What kind of questions do you want? Pick one or more.'
        ).length < 2
      ) {
        throw new Error('waiting for the second question-type prompt');
      }
    });
    await user.click(last(screen.getAllByText('Multiple choice (one answer)')));
    await user.click(last(screen.getAllByText('Continue')));

    await vi.waitFor(() => {
      if (createQuizAction.mock.calls.length !== 2) {
        throw new Error(
          `Expected createQuizAction to have been called twice after answering ` +
            `the second round, got ${createQuizAction.mock.calls.length}.`
        );
      }
    });
  });
});
