# Web Application

Main frontend interface for Memosphere learning platform.

## Tech Stack
- **Next.js 14+** with App Router
- **TypeScript** + **Tailwind CSS**
- **shadcn/ui** + **Radix UI**
- **Zustand** for state management

## Key Features
- Role-based interfaces (learner, admin, moderator, analyst)
- Real-time quiz sessions with WebSocket
- Progress tracking and analytics dashboard
- Responsive design with dark/light mode

## Development
```bash
pnpm install
cp .env.example .env.local
PORT=3000 pnpm dev
```

## Local Port: 3000