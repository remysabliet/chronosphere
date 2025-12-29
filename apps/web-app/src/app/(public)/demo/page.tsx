'use client'

import { motion } from 'framer-motion'
import { ArrowRight, Brain, Play, Sparkles } from 'lucide-react'
import Link from 'next/link'

import { ROUTES } from '@/lib/constants'
import { HeroSection } from '@/shared/components/layout/hero-section'
import { Button } from '@/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/ui/card'

const demoSteps = [
  {
    title: 'Choose a Topic',
    description: 'Select "Introduction to Psychology" to see adaptive learning in action.',
  },
  {
    title: 'Take the Quiz',
    description: 'Answer questions and watch as the AI adapts to your knowledge level.',
  },
  {
    title: 'Review Memocards',
    description: 'Explore multimedia flashcards with images, audio, and mnemonics.',
  },
  {
    title: 'See Your Progress',
    description: 'View detailed analytics showing your mastery and retention.',
  },
]

export default function DemoPage() {
  return (
    <div className="flex flex-col">
      {/* Hero Section */}
      <HeroSection
        title="Experience Adaptive Learning in Action"
        description="Try Memosphere's interactive demo to see how AI personalizes your learning journey."
        primaryCta={{
          text: 'Launch Demo',
          href: '#demo-interactive',
        }}
        secondaryCta={{
          text: 'Watch Video Tour',
          href: '#video-tour',
        }}
      />

      {/* Demo Steps */}
      <section
        className="py-24 sm:py-32"
        aria-labelledby="demo-steps-heading"
      >
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 id="demo-steps-heading" className="heading-2 mb-4">
                What You'll Experience
              </h2>
              <p className="paragraph-lg max-w-2xl mx-auto">
                Follow these steps to explore Memosphere's key features.
              </p>
            </motion.div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
            {demoSteps.map((step, index) => (
              <motion.div
                key={step.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card className="h-full hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
                  <CardHeader>
                    <div className="mb-4">
                      <span className="flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-br from-brand-500 to-blue-500 text-white font-bold text-xl">
                        {index + 1}
                      </span>
                    </div>
                    <CardTitle className="text-lg">{step.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      {step.description}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Interactive Demo Placeholder */}
      <section
        id="demo-interactive"
        className="py-24 sm:py-32 bg-muted/30"
        aria-labelledby="interactive-demo-heading"
      >
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 id="interactive-demo-heading" className="heading-2 mb-4">
                Interactive Demo
              </h2>
              <p className="paragraph-lg max-w-2xl mx-auto">
                Try a real quiz session with adaptive question selection.
              </p>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="max-w-4xl mx-auto"
          >
            <Card className="overflow-hidden border-2 border-brand-500/20">
              <div className="aspect-video bg-gradient-to-br from-brand-50 via-blue-50 to-brand-50 dark:from-brand-950 dark:via-blue-950 dark:to-brand-950 flex items-center justify-center relative">
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]" />
                <div className="relative z-10 text-center">
                  <div className="mb-6 inline-flex p-6 rounded-full bg-white dark:bg-gray-900 shadow-2xl">
                    <Play className="h-12 w-12 text-brand-500" aria-hidden="true" />
                  </div>
                  <h3 className="heading-3 mb-4">Demo Coming Soon</h3>
                  <p className="text-muted-foreground max-w-md mx-auto mb-6">
                    We're finalizing the interactive demo experience. In the meantime, you can sign up for free to access the full platform.
                  </p>
                  <Button asChild variant="gradient" size="lg">
                    <Link href={ROUTES.REGISTER}>
                      Try Full Platform Free
                      <ArrowRight className="ml-2 h-5 w-5" aria-hidden="true" />
                    </Link>
                  </Button>
                </div>
              </div>
            </Card>
          </motion.div>
        </div>
      </section>

      {/* Video Tour Placeholder */}
      <section
        id="video-tour"
        className="py-24 sm:py-32"
        aria-labelledby="video-tour-heading"
      >
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 id="video-tour-heading" className="heading-2 mb-4">
                Video Tour
              </h2>
              <p className="paragraph-lg max-w-2xl mx-auto">
                Watch a guided walkthrough of Memosphere's features.
              </p>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="max-w-4xl mx-auto"
          >
            <Card className="overflow-hidden">
              <div className="aspect-video bg-gradient-to-br from-brand-900 via-blue-900 to-brand-900 flex items-center justify-center relative">
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]" />
                <div className="relative z-10 text-center text-white">
                  <div className="mb-6 inline-flex p-6 rounded-full bg-white/10 backdrop-blur-sm">
                    <Play className="h-12 w-12 text-white" aria-hidden="true" />
                  </div>
                  <h3 className="text-2xl font-bold mb-2">Video Coming Soon</h3>
                  <p className="text-white/80">
                    We're producing a comprehensive video tour.
                  </p>
                </div>
              </div>
            </Card>
          </motion.div>
        </div>
      </section>

      {/* Features Highlight */}
      <section
        className="py-24 sm:py-32 bg-muted/30"
        aria-labelledby="highlights-heading"
      >
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 id="highlights-heading" className="heading-2 mb-4">
                What Makes Memosphere Different
              </h2>
              <p className="paragraph-lg max-w-2xl mx-auto">
                Experience these powerful features firsthand in our demo.
              </p>
            </motion.div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <Card className="h-full hover:shadow-xl transition-shadow duration-300">
                <CardHeader>
                  <div className="mb-4 inline-flex p-3 rounded-lg bg-gradient-to-br from-brand-500 to-blue-500 text-white">
                    <Brain className="h-6 w-6" aria-hidden="true" />
                  </div>
                  <CardTitle className="text-xl">Real-Time Adaptation</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">
                    Watch as the AI adjusts question difficulty based on your responses. Questions become easier or harder in real-time to match your knowledge level.
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <Card className="h-full hover:shadow-xl transition-shadow duration-300">
                <CardHeader>
                  <div className="mb-4 inline-flex p-3 rounded-lg bg-gradient-to-br from-brand-500 to-blue-500 text-white">
                    <Sparkles className="h-6 w-6" aria-hidden="true" />
                  </div>
                  <CardTitle className="text-xl">Multimedia Learning</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">
                    Interact with memocards featuring images, audio, and mnemonic techniques. Experience how multi-sensory learning improves retention.
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section
        className="py-24 sm:py-32 bg-gradient-to-br from-brand-600 via-blue-500 to-brand-500 text-white"
        aria-labelledby="demo-cta-heading"
      >
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="max-w-3xl mx-auto"
          >
            <h2
              id="demo-cta-heading"
              className="heading-1 mb-6 text-white"
            >
              Ready to Get Started?
            </h2>
            <p className="paragraph-lg mb-10 text-white/90">
              The demo is just a glimpse. Sign up free to unlock the full power of adaptive learning.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button
                asChild
                size="xl"
                variant="default"
                className="bg-white text-brand-600 hover:bg-gray-100 hover:scale-105 transition-all duration-300 shadow-2xl"
              >
                <Link href={ROUTES.REGISTER}>
                  Start Learning Free
                  <ArrowRight className="ml-2 h-5 w-5" aria-hidden="true" />
                </Link>
              </Button>
              <Button
                asChild
                size="xl"
                variant="outline"
                className="border-white text-white hover:bg-white/10"
              >
                <Link href={ROUTES.PRICING}>View Pricing</Link>
              </Button>
            </div>
            <p className="mt-6 text-sm text-white/70">
              No credit card required • Free forever plan available
            </p>
          </motion.div>
        </div>
      </section>
    </div>
  )
}
