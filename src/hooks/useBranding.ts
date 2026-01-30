"use client"

import { useState, useEffect, useCallback } from "react"

export interface BrandingTheme {
  primary: string
  primaryForeground: string
  background: string
  foreground: string
  secondary: string
  secondaryForeground: string
  accent: string
  accentForeground: string
  muted: string
  mutedForeground: string
  border: string
  card: string
  cardForeground: string
  destructive: string
  destructiveForeground: string
  popover: string
  popoverForeground: string
}

export interface BrandingConfig {
  siteName: string
  logoUrl: string
  faviconUrl?: string
  theme: BrandingTheme
  features: {
    particlesEnabled: boolean
    cyberEffects: boolean
  }
}

interface UseBrandingReturn {
  branding: BrandingConfig | null
  loading: boolean
  error: Error | null
  refresh: () => Promise<void>
}

const DEFAULT_BRANDING: BrandingConfig = {
  siteName: "Cerberus",
  logoUrl: "",
  theme: {
    primary: "hsl(217.2 91.2% 59.8%)",
    primaryForeground: "hsl(222.2 47.4% 11.2%)",
    background: "hsl(222.2 84% 4.9%)",
    foreground: "hsl(210 40% 98%)",
    secondary: "hsl(217.2 32.6% 17.5%)",
    secondaryForeground: "hsl(210 40% 98%)",
    accent: "hsl(217.2 32.6% 17.5%)",
    accentForeground: "hsl(210 40% 98%)",
    muted: "hsl(217.2 32.6% 17.5%)",
    mutedForeground: "hsl(215 20.2% 65.1%)",
    border: "hsl(217.2 32.6% 17.5%)",
    card: "hsl(222.2 84% 4.9%)",
    cardForeground: "hsl(210 40% 98%)",
    destructive: "hsl(0 62.8% 30.6%)",
    destructiveForeground: "hsl(210 40% 98%)",
    popover: "hsl(222.2 84% 4.9%)",
    popoverForeground: "hsl(210 40% 98%)",
  },
  features: {
    particlesEnabled: true,
    cyberEffects: true,
  },
}

function parseHslToCssVars(theme: BrandingTheme): Record<string, string> {
  const cssVars: Record<string, string> = {}
  
  for (const [key, value] of Object.entries(theme)) {
    const cssVar = key.replace(/([A-Z])/g, '-$1').toLowerCase().replace(/^-/, '--')
    cssVars[cssVar] = value
  }

  return cssVars
}

function applyThemeToRoot(cssVars: Record<string, string>) {
  if (typeof document === "undefined") return

  const root = document.documentElement
  
  for (const [key, value] of Object.entries(cssVars)) {
    root.style.setProperty(key, value)
  }
}

export function useBranding(): UseBrandingReturn {
  const [branding, setBranding] = useState<BrandingConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchBranding = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch("/api/admin/config/branding")

      if (!response.ok) {
        // If API returns 404 or error, use default branding
        console.warn("Branding API not available, using defaults")
        setBranding(DEFAULT_BRANDING)
        applyThemeToRoot(parseHslToCssVars(DEFAULT_BRANDING.theme))
        return
      }

      const data = await response.json()
      const config: BrandingConfig = {
        siteName: data.siteName || DEFAULT_BRANDING.siteName,
        logoUrl: data.logoUrl || DEFAULT_BRANDING.logoUrl,
        faviconUrl: data.faviconUrl,
        theme: {
          primary: data.theme?.primary || DEFAULT_BRANDING.theme.primary,
          primaryForeground: data.theme?.primaryForeground || DEFAULT_BRANDING.theme.primaryForeground,
          background: data.theme?.background || DEFAULT_BRANDING.theme.background,
          foreground: data.theme?.foreground || DEFAULT_BRANDING.theme.foreground,
          secondary: data.theme?.secondary || DEFAULT_BRANDING.theme.secondary,
          secondaryForeground: data.theme?.secondaryForeground || DEFAULT_BRANDING.theme.secondaryForeground,
          accent: data.theme?.accent || DEFAULT_BRANDING.theme.accent,
          accentForeground: data.theme?.accentForeground || DEFAULT_BRANDING.theme.accentForeground,
          muted: data.theme?.muted || DEFAULT_BRANDING.theme.muted,
          mutedForeground: data.theme?.mutedForeground || DEFAULT_BRANDING.theme.mutedForeground,
          border: data.theme?.border || DEFAULT_BRANDING.theme.border,
          card: data.theme?.card || DEFAULT_BRANDING.theme.card,
          cardForeground: data.theme?.cardForeground || DEFAULT_BRANDING.theme.cardForeground,
          destructive: data.theme?.destructive || DEFAULT_BRANDING.theme.destructive,
          destructiveForeground: data.theme?.destructiveForeground || DEFAULT_BRANDING.theme.destructiveForeground,
          popover: data.theme?.popover || DEFAULT_BRANDING.theme.popover,
          popoverForeground: data.theme?.popoverForeground || DEFAULT_BRANDING.theme.popoverForeground,
        },
        features: {
          particlesEnabled: data.features?.particlesEnabled ?? DEFAULT_BRANDING.features.particlesEnabled,
          cyberEffects: data.features?.cyberEffects ?? DEFAULT_BRANDING.features.cyberEffects,
        },
      }

      setBranding(config)
      applyThemeToRoot(parseHslToCssVars(config.theme))
    } catch (err) {
      console.error("Failed to fetch branding:", err)
      setError(err instanceof Error ? err : new Error("Failed to fetch branding"))
      // Apply default theme on error
      setBranding(DEFAULT_BRANDING)
      applyThemeToRoot(parseHslToCssVars(DEFAULT_BRANDING.theme))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchBranding()
  }, [fetchBranding])

  return {
    branding,
    loading,
    error,
    refresh: fetchBranding,
  }
}

export function useTheme() {
  const { branding } = useBranding()

  const applyTheme = useCallback((theme: Partial<BrandingTheme>) => {
    if (!branding) return

    const mergedTheme = { ...branding.theme, ...theme }
    const cssVars = parseHslToCssVars(mergedTheme)
    applyThemeToRoot(cssVars)
  }, [branding])

  return { applyTheme, currentTheme: branding?.theme }
}

export { DEFAULT_BRANDING, parseHslToCssVars, applyThemeToRoot }
