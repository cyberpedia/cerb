"use client"

import { createContext, useContext, useEffect, useState, ReactNode } from "react"
import { BrandingTheme, useBranding } from "@/hooks/useBranding"

interface ThemeContextType {
  theme: BrandingTheme | null
  isDark: boolean
  toggleTheme: () => void
  setTheme: (theme: Partial<BrandingTheme>) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { branding, loading } = useBranding()
  const [isDark, setIsDark] = useState(true)

  useEffect(() => {
    // Initialize theme based on branding or system preference
    if (branding?.theme) {
      // Check if the theme has a light/dark indicator
      const bg = branding.theme.background
      const isLight = bg.includes("0 0% 100%") || bg.includes("hsl(0 0% 100%)")
      setIsDark(!isLight)
    } else {
      // Default to dark mode
      setIsDark(true)
    }
  }, [branding])

  useEffect(() => {
    // Apply dark/light class to document
    const root = document.documentElement
    if (isDark) {
      root.classList.remove("light")
      root.classList.add("dark")
    } else {
      root.classList.remove("dark")
      root.classList.add("light")
    }
  }, [isDark])

  const toggleTheme = () => {
    setIsDark((prev: boolean) => !prev)
  }

  const setTheme = (newTheme: Partial<BrandingTheme>) => {
    if (!branding) return

    const root = document.documentElement
    const theme = { ...branding.theme, ...newTheme }

    // Apply CSS variables
    for (const [key, value] of Object.entries(theme)) {
      const cssVar = key.replace(/([A-Z])/g, "-$1").toLowerCase()
      root.style.setProperty(`--${cssVar}`, value)
    }
  }

  return (
    <ThemeContext.Provider
      value={{
        theme: branding?.theme || null,
        isDark,
        toggleTheme,
        setTheme,
      }}
    >
      <div className={isDark ? "dark" : "light"}>{children}</div>
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider")
  }
  return context
}
