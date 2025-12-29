'use client'

import { AnimatePresence, motion } from 'framer-motion'
import { Brain, Menu, X } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import * as React from 'react'

import { ROUTES } from '@/lib/constants'
import { cn } from '@/lib/utils'
import { Button } from '@/ui/button'

const navigation = [
  { name: 'Features', href: ROUTES.FEATURES },
  { name: 'Pricing', href: ROUTES.PRICING },
  { name: 'About', href: ROUTES.ABOUT },
  { name: 'Demo', href: ROUTES.DEMO },
]

export function Header() {
  const pathname = usePathname()
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false)
  const [scrolled, setScrolled] = React.useState(false)

  // Handle scroll effect
  React.useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // Close mobile menu on route change
  React.useEffect(() => {
    setMobileMenuOpen(false)
  }, [pathname])

  return (
    <header
      className={cn(
        'fixed top-0 z-50 w-full transition-all duration-300',
        scrolled
          ? 'bg-background/80 backdrop-blur-lg border-b shadow-sm'
          : 'bg-transparent'
      )}
    >
      <nav
        className="container mx-auto flex items-center justify-between px-4 sm:px-6 lg:px-8 py-4"
        aria-label="Global navigation"
      >
        {/* Logo */}
        <div className="flex lg:flex-1">
          <Link
            href={ROUTES.HOME}
            className="flex items-center gap-2 group"
            aria-label="Memosphere home"
          >
            <div className="relative">
              <Brain className="h-8 w-8 text-brand-600 transition-transform group-hover:scale-110" />
              <div className="absolute inset-0 -z-10 blur-xl bg-brand-500/20 rounded-full scale-0 group-hover:scale-150 transition-transform" />
            </div>
            <span className="text-xl font-bold gradient-text">Memosphere</span>
          </Link>
        </div>

        {/* Mobile menu button */}
        <div className="flex lg:hidden">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="-m-2.5 inline-flex items-center justify-center rounded-md p-2.5 text-foreground hover:bg-accent transition-colors"
            aria-expanded={mobileMenuOpen}
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? (
              <X className="h-6 w-6" aria-hidden="true" />
            ) : (
              <Menu className="h-6 w-6" aria-hidden="true" />
            )}
          </button>
        </div>

        {/* Desktop navigation */}
        <div className="hidden lg:flex lg:gap-x-8" role="navigation">
          {navigation.map((item) => (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'text-sm font-medium transition-colors relative py-2',
                pathname === item.href
                  ? 'text-brand-600'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {item.name}
              {pathname === item.href && (
                <motion.div
                  layoutId="navbar-indicator"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-600"
                  transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                />
              )}
            </Link>
          ))}
        </div>

        {/* CTA buttons */}
        <div className="hidden lg:flex lg:flex-1 lg:justify-end lg:gap-x-4">
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="font-medium"
          >
            <Link href={ROUTES.LOGIN}>Log in</Link>
          </Button>
          <Button
            asChild
            variant="gradient"
            size="sm"
            className="font-medium"
          >
            <Link href={ROUTES.REGISTER}>Get Started</Link>
          </Button>
        </div>
      </nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="lg:hidden border-t"
            role="dialog"
            aria-label="Mobile menu"
          >
            <div className="space-y-1 px-4 pb-4 pt-4 bg-background/95 backdrop-blur-lg">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    'block rounded-md px-3 py-2 text-base font-medium transition-colors',
                    pathname === item.href
                      ? 'bg-accent text-accent-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                  )}
                >
                  {item.name}
                </Link>
              ))}
              <div className="pt-4 space-y-2">
                <Button
                  asChild
                  variant="outline"
                  className="w-full"
                >
                  <Link href={ROUTES.LOGIN}>Log in</Link>
                </Button>
                <Button
                  asChild
                  variant="gradient"
                  className="w-full"
                >
                  <Link href={ROUTES.REGISTER}>Get Started</Link>
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
