"use client"

import { useState, useCallback } from "react"
import { motion } from "framer-motion"
import { Palette, Save, RefreshCw, Check } from "lucide-react"
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

interface ThemeColors {
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

interface BrandingConfig {
  siteName: string
  logoUrl: string
  faviconUrl?: string
  theme: ThemeColors
  features: {
    particlesEnabled: boolean
    cyberEffects: boolean
  }
}

const DEFAULT_THEME: ThemeColors = {
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
}

interface ColorPickerFieldProps {
  label: string
  value: string
  onChange: (value: string) => void
  description?: string
}

function ColorPickerField({ label, value, onChange, description }: ColorPickerFieldProps) {
  // Convert HSL to Hex for the color input
  const hslToHex = (hsl: string): string => {
    const match = hsl.match(/hsl\((\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)%\s+(\d+(?:\.\d+)?)%\)/)
    if (!match) return "#3b82f6"
    
    const h = parseFloat(match[1]) / 360
    const s = parseFloat(match[2]) / 100
    const l = parseFloat(match[3]) / 100
    
    let r: number, g: number, b: number
    
    if (s === 0) {
      r = g = b = l
    } else {
      const hue2rgb = (p: number, q: number, t: number) => {
        if (t < 0) t += 1
        if (t > 1) t -= 1
        if (t < 1/6) return p + (q - p) * 6 * t
        if (t < 1/2) return q
        if (t < 2/3) return p + (q - p) * (2/3 - t) * 6
        return p
      }
      
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s
      const p = 2 * l - q
      r = hue2rgb(p, q, h + 1/3)
      g = hue2rgb(p, q, h)
      b = hue2rgb(p, q, h - 1/3)
    }
    
    const toHex = (c: number) => {
      const hex = Math.round(c * 255).toString(16)
      return hex.length === 1 ? "0" + hex : hex
    }
    
    return `#${toHex(r)}${toHex(g)}${toHex(b)}`
  }
  
  // Convert Hex to HSL
  const hexToHsl = (hex: string): string => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
    if (!result) return value
    
    let r = parseInt(result[1], 16) / 255
    let g = parseInt(result[2], 16) / 255
    let b = parseInt(result[3], 16) / 255
    
    const max = Math.max(r, g, b)
    const min = Math.min(r, g, b)
    let h = 0, s = 0, l = (max + min) / 2
    
    if (max !== min) {
      const d = max - min
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
      switch (max) {
        case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break
        case g: h = ((b - r) / d + 2) / 6; break
        case b: h = ((r - g) / d + 4) / 6; break
      }
    }
    
    return `hsl(${Math.round(h * 360)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%)`
  }
  
  const hexValue = hslToHex(value)
  
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-foreground">{label}</label>
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
      <div className="flex items-center gap-3">
        <div className="relative">
          <input
            type="color"
            value={hexValue}
            onChange={(e) => onChange(hexToHsl(e.target.value))}
            className="w-10 h-10 rounded-lg border border-border cursor-pointer bg-transparent"
          />
          <div 
            className="absolute inset-0 rounded-lg pointer-events-none"
            style={{ backgroundColor: value }}
          />
        </div>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 px-3 py-2 bg-background border border-border rounded-lg text-sm font-mono text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
      </div>
    </div>
  )
}

interface ThemeEditorProps {
  initialConfig?: BrandingConfig
  onSave?: (config: BrandingConfig) => Promise<void>
}

export function ThemeEditor({ initialConfig, onSave }: ThemeEditorProps) {
  const [config, setConfig] = useState<BrandingConfig>(initialConfig || {
    siteName: "Cerberus",
    logoUrl: "",
    theme: DEFAULT_THEME,
    features: {
      particlesEnabled: true,
      cyberEffects: true,
    },
  })
  
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const updateThemeColor = useCallback((key: keyof ThemeColors, value: string) => {
    setConfig(prev => ({
      ...prev,
      theme: {
        ...prev.theme,
        [key]: value,
      },
    }))
    setSaved(false)
  }, [])
  
  const handleSave = async () => {
    setSaving(true)
    setError(null)
    
    try {
      // Save to API
      const response = await fetch("/api/admin/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          branding: {
            site_name: config.siteName,
            logo_url: config.logoUrl,
          },
          theme: {
            primary_color_hex: config.theme.primary.match(/hsl\(\d+\.?\d*\s+([\d.]+)%\s+([\d.]+)%\)/)?.[0] || "#3b82f6",
            bg_color_hex: config.theme.background.match(/hsl\(\d+\.?\d*\s+([\d.]+)%\s+([\d.]+)%\)/)?.[0] || "#0f172a",
            font_family: "Inter",
          },
        }),
      })
      
      if (!response.ok) {
        throw new Error("Failed to save theme configuration")
      }
      
      if (onSave) {
        await onSave(config)
      }
      
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save")
    } finally {
      setSaving(false)
    }
  }
  
  const handleReset = () => {
    setConfig(prev => ({
      ...prev,
      theme: DEFAULT_THEME,
    }))
    setSaved(false)
  }
  
  const themeGroups = [
    {
      title: "Primary Colors",
      colors: [
        { key: "primary" as const, label: "Primary", description: "Main brand color" },
        { key: "primaryForeground" as const, label: "Primary Foreground", description: "Text on primary color" },
      ],
    },
    {
      title: "Background & Foreground",
      colors: [
        { key: "background" as const, label: "Background", description: "Page background" },
        { key: "foreground" as const, label: "Foreground", description: "Main text color" },
      ],
    },
    {
      title: "Secondary Colors",
      colors: [
        { key: "secondary" as const, label: "Secondary", description: "Secondary elements" },
        { key: "secondaryForeground" as const, label: "Secondary Foreground", description: "Text on secondary" },
      ],
    },
    {
      title: "Accent & Muted",
      colors: [
        { key: "accent" as const, label: "Accent", description: "Highlight elements" },
        { key: "accentForeground" as const, label: "Accent Foreground", description: "Text on accent" },
        { key: "muted" as const, label: "Muted", description: "Subtle backgrounds" },
        { key: "mutedForeground" as const, label: "Muted Foreground", description: "Secondary text" },
      ],
    },
    {
      title: "UI Elements",
      colors: [
        { key: "card" as const, label: "Card", description: "Card backgrounds" },
        { key: "cardForeground" as const, label: "Card Foreground", description: "Text on cards" },
        { key: "popover" as const, label: "Popover", description: "Dropdown backgrounds" },
        { key: "popoverForeground" as const, label: "Popover Foreground", description: "Text in popovers" },
        { key: "border" as const, label: "Border", description: "Border color" },
      ],
    },
    {
      title: "Status Colors",
      colors: [
        { key: "destructive" as const, label: "Destructive", description: "Error/danger color" },
        { key: "destructiveForeground" as const, label: "Destructive Foreground", description: "Text on destructive" },
      ],
    },
  ]
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Palette className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">Theme Editor</h3>
            <p className="text-sm text-muted-foreground">Customize your platform's appearance</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground bg-muted hover:bg-muted/80 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className="w-4 h-4" />
            Reset
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className={cn(
              "flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all disabled:opacity-50",
              saved
                ? "bg-green-500 text-white"
                : "bg-primary text-primary-foreground hover:bg-primary/90"
            )}
          >
            {saved ? (
              <>
                <Check className="w-4 h-4" />
                Saved!
              </>
            ) : saving ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Theme
              </>
            )}
          </button>
        </div>
      </div>
      
      {/* Error Message */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg"
        >
          <p className="text-sm text-destructive">{error}</p>
        </motion.div>
      )}
      
      {/* Preview */}
      <div className="p-6 bg-card border border-border rounded-xl">
        <h4 className="text-sm font-medium text-foreground mb-4">Live Preview</h4>
        <div 
          className="p-6 rounded-lg space-y-4"
          style={{ backgroundColor: config.theme.background }}
        >
          <div className="flex items-center gap-4">
            <button
              className="px-4 py-2 rounded-lg font-medium transition-colors"
              style={{ 
                backgroundColor: config.theme.primary,
                color: config.theme.primaryForeground,
              }}
            >
              Primary Button
            </button>
            <button
              className="px-4 py-2 rounded-lg font-medium transition-colors"
              style={{ 
                backgroundColor: config.theme.secondary,
                color: config.theme.secondaryForeground,
              }}
            >
              Secondary
            </button>
            <button
              className="px-4 py-2 rounded-lg font-medium transition-colors"
              style={{ 
                backgroundColor: config.theme.accent,
                color: config.theme.accentForeground,
              }}
            >
              Accent
            </button>
          </div>
          <div 
            className="p-4 rounded-lg border"
            style={{ 
              backgroundColor: config.theme.card,
              color: config.theme.cardForeground,
              borderColor: config.theme.border,
            }}
          >
            <p style={{ color: config.theme.foreground }}>Card content with foreground text</p>
            <p style={{ color: config.theme.mutedForeground }}>Muted text for secondary information</p>
          </div>
        </div>
      </div>
      
      {/* Color Groups */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {themeGroups.map((group) => (
          <motion.div
            key={group.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-6 bg-card border border-border rounded-xl space-y-4"
          >
            <h4 className="text-sm font-semibold text-foreground border-b border-border pb-2">
              {group.title}
            </h4>
            <div className="space-y-4">
              {group.colors.map((color) => (
                <ColorPickerField
                  key={color.key}
                  label={color.label}
                  value={config.theme[color.key]}
                  onChange={(value) => updateThemeColor(color.key, value)}
                  description={color.description}
                />
              ))}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
