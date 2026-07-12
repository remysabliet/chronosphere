/**
 * Application-wide constants
 */

export const APP_NAME = 'Memosphere';
export const APP_DESCRIPTION =
  'AI-powered adaptive learning platform with multimedia quizzes and spaced repetition';

export const ROUTES = {
  // Public routes
  HOME: '/',
  ABOUT: '/about',
  FEATURES: '/features',
  PRICING: '/pricing',
  DEMO: '/demo',
  TERMS: '/terms',
  PRIVACY: '/privacy',

  // Auth routes
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',

  // Authenticated routes
  HOME_APP: '/app/home',
  PROFILE: '/app/profile',
  QUIZZES: '/app/quizzes',
  QUIZ_DETAIL: (id: string) => `/app/quizzes/${id}`,
  QUIZ_NEW: '/app/quiz/new',
  QUIZ_NEW_MANUAL: '/app/quiz/new/manual',
  SESSION: (id: string) => `/app/sessions/${id}`,
  MEMOCARDS: '/app/memocards',
  ANALYTICS: '/app/analytics',

  // Admin routes
  ADMIN_DASHBOARD: '/admin/dashboard',
  ADMIN_USERS: '/admin/users',
  ADMIN_QUESTIONS: '/admin/questions',
} as const;

// The post-login landing page. One place to flip when Home ships (see
// docs/product/ui-update-plan.md §1).
export const DEFAULT_AUTHENTICATED_ROUTE = ROUTES.QUIZZES;

export const EXTERNAL_LINKS = {
  GITHUB: 'https://github.com/memosphere',
  TWITTER: 'https://twitter.com/memosphere',
  LINKEDIN: 'https://linkedin.com/company/memosphere',
  SUPPORT: 'mailto:support@memosphere.com',
} as const;

export const FEATURES = [
  {
    title: 'Adaptive Learning',
    description:
      'AI adjusts difficulty in real-time based on your performance using BKT and IRT algorithms.',
    icon: 'brain',
  },
  {
    title: 'Spaced Repetition',
    description:
      'Scientifically proven SM-2 algorithm ensures long-term retention and optimal review timing.',
    icon: 'calendar',
  },
  {
    title: 'Multimedia Learning',
    description:
      'Interactive memocards with images, audio, and visual mnemonics for multi-sensory learning.',
    icon: 'image',
  },
  {
    title: 'Progress Analytics',
    description:
      'Track your mastery across concepts with detailed visualizations and insights.',
    icon: 'chart',
  },
  {
    title: 'Question Variety',
    description:
      'MCQ, fill-in-blank, matching, ordering, and listening comprehension questions.',
    icon: 'layers',
  },
  {
    title: 'Gamification',
    description:
      'Earn achievements, maintain streaks, and compete on leaderboards.',
    icon: 'trophy',
  },
] as const;

export const PRICING_TIERS = [
  {
    name: 'Free',
    price: 0,
    description: 'Perfect for trying out Memosphere',
    features: [
      '50 questions per month',
      'Basic analytics',
      '3 memocard decks',
      'Email support',
    ],
    cta: 'Get Started',
    popular: false,
  },
  {
    name: 'Pro',
    price: 9.99,
    description: 'For serious learners',
    features: [
      'Unlimited questions',
      'Advanced analytics',
      'Unlimited memocard decks',
      'Priority support',
      'Custom learning paths',
      'Export progress data',
    ],
    cta: 'Start Free Trial',
    popular: true,
  },
  {
    name: 'Enterprise',
    price: null,
    description: 'For teams and organizations',
    features: [
      'Everything in Pro',
      'Team management',
      'SSO authentication',
      'Custom integrations',
      'Dedicated support',
      'SLA guarantee',
    ],
    cta: 'Contact Sales',
    popular: false,
  },
] as const;

export const TESTIMONIALS = [
  {
    name: 'Sarah Chen',
    role: 'Medical Student',
    avatar: '/avatars/sarah.jpg',
    content:
      'Memosphere helped me ace my anatomy exam. The spaced repetition is a game-changer!',
    rating: 5,
  },
  {
    name: 'Marcus Johnson',
    role: 'Software Engineer',
    avatar: '/avatars/marcus.jpg',
    content:
      'Learning React has never been easier. The adaptive difficulty keeps me challenged but not overwhelmed.',
    rating: 5,
  },
  {
    name: 'Aiko Tanaka',
    role: 'Language Learner',
    avatar: '/avatars/aiko.jpg',
    content:
      'The multimedia flashcards with audio pronunciation are perfect for learning Japanese!',
    rating: 5,
  },
] as const;

export const BLOG_POSTS = [
  {
    title: 'How Spaced Repetition Works',
    slug: 'how-spaced-repetition-works',
    excerpt:
      "Discover the science behind the SM-2 algorithm and why it's so effective for long-term retention.",
    publishedAt: '2024-03-15',
    readTime: 5,
    category: 'Learning Science',
  },
  {
    title: 'Adaptive Learning with BKT and IRT',
    slug: 'adaptive-learning-bkt-irt',
    excerpt:
      'Learn how Bayesian Knowledge Tracing and Item Response Theory personalize your learning experience.',
    publishedAt: '2024-03-10',
    readTime: 8,
    category: 'Technology',
  },
  {
    title: 'Best Practices for Creating Memocards',
    slug: 'best-practices-memocards',
    excerpt:
      'Tips and tricks for creating effective flashcards that stick in your memory.',
    publishedAt: '2024-03-05',
    readTime: 6,
    category: 'Tips & Tricks',
  },
] as const;

export const FAQ = [
  {
    question: 'How does the adaptive learning work?',
    answer:
      "Memosphere uses BKT (Bayesian Knowledge Tracing) and IRT (Item Response Theory) algorithms to assess your knowledge level and adjust question difficulty in real-time. This ensures you're always challenged at the optimal level for learning.",
  },
  {
    question: 'What is spaced repetition?',
    answer:
      "Spaced repetition is a scientifically proven learning technique that schedules review sessions at increasing intervals. Our SM-2 algorithm ensures you review concepts right before you're about to forget them, maximizing retention.",
  },
  {
    question: 'Can I create my own questions?',
    answer:
      'Yes! Pro users can create custom questions and memocard decks. You can also import content from text, PDFs, or even audio files.',
  },
  {
    question: 'Is my data secure?',
    answer:
      "Absolutely. We use industry-standard encryption for data in transit and at rest. We're GDPR compliant and never sell your data to third parties.",
  },
  {
    question: 'Can I use Memosphere offline?',
    answer:
      'Memocard review is available offline via our Progressive Web App. Quiz sessions require an internet connection for AI-powered adaptive features.',
  },
] as const;

export const SOCIAL_PROOF = {
  users: '10,000+',
  questions: '1M+',
  accuracy: '95%',
  satisfaction: '4.9/5',
} as const;

export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
export const ALLOWED_IMAGE_TYPES = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
];
export const ALLOWED_AUDIO_TYPES = ['audio/mpeg', 'audio/wav', 'audio/ogg'];
export const ALLOWED_DOCUMENT_TYPES = ['application/pdf', 'text/plain'];

export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
} as const;

export const TIMEOUTS = {
  TOAST: 5000, // 5 seconds
  DEBOUNCE: 300, // 300ms
  THROTTLE: 1000, // 1 second
} as const;
