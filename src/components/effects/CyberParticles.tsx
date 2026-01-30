"use client"

import { useEffect, useRef, useCallback } from "react"
import { useBranding } from "@/hooks/useBranding"

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  opacity: number
  color: string
}

interface CyberParticlesProps {
  enabled?: boolean
  particleCount?: number
  connectionDistance?: number
}

export function CyberParticles({
  enabled = true,
  particleCount = 100,
  connectionDistance = 150,
}: CyberParticlesProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const particlesRef = useRef<Particle[]>([])
  const animationRef = useRef<number>(0)
  const { branding } = useBranding()

  const createParticle = useCallback((width: number, height: number): Particle => {
    const primaryColor = branding?.theme?.primary || "hsl(217.2 91.2% 59.8%)"
    
    return {
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      size: Math.random() * 2 + 1,
      opacity: Math.random() * 0.5 + 0.2,
      color: primaryColor,
    }
  }, [branding])

  const initParticles = useCallback((width: number, height: number) => {
    particlesRef.current = Array.from({ length: particleCount }, () =>
      createParticle(width, height)
    )
  }, [particleCount, createParticle])

  const drawParticles = useCallback(
    (ctx: CanvasRenderingContext2D, width: number, height: number) => {
      ctx.clearRect(0, 0, width, height)

      const particles = particlesRef.current

      // Update and draw particles
      particles.forEach((particle, i) => {
        // Update position
        particle.x += particle.vx
        particle.y += particle.vy

        // Bounce off edges
        if (particle.x < 0 || particle.x > width) particle.vx *= -1
        if (particle.y < 0 || particle.y > height) particle.vy *= -1

        // Draw particle
        ctx.beginPath()
        ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2)
        ctx.fillStyle = particle.color.replace(")", `, ${particle.opacity})`).replace("hsl", "hsla")
        ctx.fill()

        // Draw connections
        for (let j = i + 1; j < particles.length; j++) {
          const other = particles[j]
          const dx = particle.x - other.x
          const dy = particle.y - other.y
          const distance = Math.sqrt(dx * dx + dy * dy)

          if (distance < connectionDistance) {
            const opacity = 1 - distance / connectionDistance
            ctx.beginPath()
            ctx.moveTo(particle.x, particle.y)
            ctx.lineTo(other.x, other.y)
            ctx.strokeStyle = particle.color
              .replace(")", `, ${opacity * 0.3})`)
              .replace("hsl", "hsla")
            ctx.lineWidth = 0.5
            ctx.stroke()
          }
        }
      })
    },
    [connectionDistance]
  )

  useEffect(() => {
    if (!enabled || !canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const handleResize = () => {
      const parent = canvas.parentElement
      if (!parent) return

      canvas.width = parent.clientWidth
      canvas.height = parent.clientHeight
      initParticles(canvas.width, canvas.height)
    }

    handleResize()
    window.addEventListener("resize", handleResize)

    const animate = () => {
      drawParticles(ctx, canvas.width, canvas.height)
      animationRef.current = requestAnimationFrame(animate)
    }

    animate()

    return () => {
      window.removeEventListener("resize", handleResize)
      cancelAnimationFrame(animationRef.current)
    }
  }, [enabled, drawParticles, initParticles])

  // Update particle colors when branding changes
  useEffect(() => {
    if (!branding?.theme?.primary) return

    const primaryColor = branding.theme.primary
    particlesRef.current.forEach((particle) => {
      particle.color = primaryColor
    })
  }, [branding?.theme?.primary])

  if (!enabled) return null

  return (
    <canvas
      ref={canvasRef}
      id="particles-canvas"
      className="fixed inset-0 pointer-events-none z-0"
    />
  )
}

// Simplified particle effect for headers/cards
export function MiniParticles({ count = 20 }: { count?: number }) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const container = containerRef.current
    const particles: HTMLDivElement[] = []

    for (let i = 0; i < count; i++) {
      const particle = document.createElement("div")
      particle.className = "absolute w-1 h-1 bg-primary rounded-full opacity-0"
      particle.style.left = `${Math.random() * 100}%`
      particle.style.top = `${Math.random() * 100}%`
      particle.style.animationDelay = `${Math.random() * 2}s`
      particle.style.animationDuration = `${Math.random() * 3 + 2}s`
      container.appendChild(particle)
      particles.push(particle)
    }

    // Add animation styles
    const style = document.createElement("style")
    style.textContent = `
      @keyframes float-particle {
        0%, 100% { transform: translateY(0) scale(1); opacity: 0; }
        50% { transform: translateY(-20px) scale(1.5); opacity: 1; }
      }
    `
    document.head.appendChild(style)

    particles.forEach((p) => {
      p.style.animationName = "float-particle"
      p.style.animationIterationCount = "infinite"
      p.style.animationTimingFunction = "ease-in-out"
    })

    return () => {
      particles.forEach((p) => p.remove())
      style.remove()
    }
  }, [count])

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 overflow-hidden pointer-events-none"
    />
  )
}
