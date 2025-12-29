'use client'

import { motion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import * as React from 'react'

import { cn } from '@/lib/utils'
import { Button } from '@/ui/button'

interface HeroSectionProps {
  title: string
  description?: string
  primaryCta?: {
    text: string
    href: string
  }
  secondaryCta?: {
    text: string
    href: string
  }
  showDecoration?: boolean
  children?: React.ReactNode
  className?: string
}

export function HeroSection({
  title,
  description,
  primaryCta,
  secondaryCta,
  showDecoration = true,
  children,
  className,
}: HeroSectionProps) {
  return (
    <section
      className={cn(
        'relative overflow-hidden bg-gradient-to-br from-background via-brand-50/30 to-blue-50/30 dark:from-background dark:via-brand-950/30 dark:to-blue-950/30',
        className
      )}
      aria-labelledby="hero-title"
    >
      {/* Decorative background elements */}
      {showDecoration && (
        <>
          <div className="absolute inset-0 -z-10">
            {/* Animated gradient orbs */}
            <div className="absolute top-0 -left-4 w-72 h-72 bg-brand-400 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob" />
            <div className="absolute top-0 -right-4 w-72 h-72 bg-blue-400 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000" />
            <div className="absolute -bottom-8 left-20 w-72 h-72 bg-brand-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000" />
          </div>

          {/* Grid pattern */}
          <div
            className="absolute inset-0 -z-10 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"
            aria-hidden="true"
          />
        </>
      )}

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-24 sm:py-32 lg:py-40">
        <div className="mx-auto max-w-4xl text-center">
          {/* Title */}
          <motion.h1
            id="hero-title"
            className="heading-1 text-balance mb-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            {title}
          </motion.h1>

          {/* Description */}
          {description && (
            <motion.p
              className="paragraph-lg max-w-2xl mx-auto mb-10"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              {description}
            </motion.p>
          )}

          {/* CTA buttons */}
          {(primaryCta || secondaryCta) && (
            <motion.div
              className="flex flex-col sm:flex-row gap-4 justify-center items-center"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              {primaryCta && (
                <Button
                  size="xl"
                  variant="gradient"
                  className="group w-full sm:w-auto"
                  asChild
                >
                  <a href={primaryCta.href}>
                    {primaryCta.text}
                    <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
                  </a>
                </Button>
              )}
              {secondaryCta && (
                <Button
                  size="xl"
                  variant="outline"
                  className="w-full sm:w-auto"
                  asChild
                >
                  <a href={secondaryCta.href}>{secondaryCta.text}</a>
                </Button>
              )}
            </motion.div>
          )}

          {/* Custom children */}
          {children && (
            <motion.div
              className="mt-12"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              {children}
            </motion.div>
          )}
        </div>
      </div>
    </section>
  )
}
