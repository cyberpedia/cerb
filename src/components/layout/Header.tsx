/// <reference types="react" />

"use client"

import Link from "next/link"
import { useBranding } from "@/hooks/useBranding"
import { Shield, Menu, X } from "lucide-react"
import { ReactNode, useState, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"

export function Header() {
  const { branding, loading } = useBranding()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20)
    }
    window.addEventListener("scroll", handleScroll)
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  const siteName = branding?.siteName || "Cerberus"
  const logoUrl = branding?.logoUrl

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-background/80 backdrop-blur-lg border-b border-border"
          : "bg-transparent"
      }`}
    >
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo Section */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="relative">
              {logoUrl ? (
                <img
                  src={logoUrl}
                  alt={siteName}
                  className="h-10 w-auto transition-transform duration-300 group-hover:scale-105"
                />
              ) : (
                <div className="relative">
                  <Shield className="h-10 w-10 text-primary transition-all duration-300 group-hover:text-primary/80" />
                  <motion.div
                    className="absolute inset-0 text-primary opacity-0 group-hover:opacity-20"
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <Shield className="h-10 w-10" />
                  </motion.div>
                </div>
              )}
            </div>
            <span className="text-xl font-bold tracking-tight transition-colors duration-300">
              {loading ? (
                <span className="animate-pulse">Loading...</span>
              ) : (
                <motion.span
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="bg-gradient-to-r from-primary to-primary/50 bg-clip-text text-transparent"
                >
                  {siteName}
                </motion.span>
              )}
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-6">
            <NavLink href="/challenges">Challenges</NavLink>
            <NavLink href="/leaderboard">Leaderboard</NavLink>
            <NavLink href="/teams">Teams</NavLink>
            <NavLink href="/docs">Documentation</NavLink>
          </nav>

          {/* Desktop Actions */}
          <div className="hidden md:flex items-center gap-4">
            <Link
              href="/auth/login"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/auth/register"
              className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 transition-all duration-200 cyber-glow"
            >
              Get Started
            </Link>
          </div>

          {/* Mobile Menu Toggle */}
          <button
            className="md:hidden p-2 text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden border-t border-border bg-background/95 backdrop-blur-lg"
          >
            <nav className="container mx-auto px-4 py-4 flex flex-col gap-2">
              <MobileNavLink href="/challenges" onClick={() => setIsMobileMenuOpen(false)}>
                Challenges
              </MobileNavLink>
              <MobileNavLink href="/leaderboard" onClick={() => setIsMobileMenuOpen(false)}>
                Leaderboard
              </MobileNavLink>
              <MobileNavLink href="/teams" onClick={() => setIsMobileMenuOpen(false)}>
                Teams
              </MobileNavLink>
              <MobileNavLink href="/docs" onClick={() => setIsMobileMenuOpen(false)}>
                Documentation
              </MobileNavLink>
              <div className="border-t border-border my-2 pt-2 flex flex-col gap-2">
                <Link
                  href="/auth/login"
                  className="text-center py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Sign In
                </Link>
                <Link
                  href="/auth/register"
                  className="text-center py-2 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Get Started
                </Link>
              </div>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}

function NavLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors relative group"
    >
      {children}
      <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary transition-all duration-300 group-hover:w-full" />
    </Link>
  )
}

function MobileNavLink({
  href,
  children,
  onClick,
}: {
  href: string
  children: ReactNode
  onClick: () => void
}) {
  return (
    <Link
      href={href}
      className="py-3 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors border-b border-border/50"
      onClick={onClick}
    >
      {children}
    </Link>
  )
}
