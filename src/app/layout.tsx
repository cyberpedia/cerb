import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { ThemeProvider } from "@/components/layout/ThemeProvider"
import { Header } from "@/components/layout/Header"
import { CyberParticles } from "@/components/effects/CyberParticles"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: {
    default: "Cerberus - Security Challenge Platform",
    template: "%s | Cerberus",
  },
  description:
    "A comprehensive security challenge platform for learning and testing cybersecurity skills.",
  keywords: [
    "cybersecurity",
    "security challenges",
    "CTF",
    "penetration testing",
    "security training",
  ],
  authors: [{ name: "Cerberus Team" }],
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://cerberus.example.com",
    siteName: "Cerberus",
    title: "Cerberus - Security Challenge Platform",
    description:
      "A comprehensive security challenge platform for learning and testing cybersecurity skills.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Cerberus Platform",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Cerberus - Security Challenge Platform",
    description:
      "A comprehensive security challenge platform for learning and testing cybersecurity skills.",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} antialiased min-h-screen bg-background text-foreground`}>
        <ThemeProvider>
          {/* Cyber Particles Background - Toggleable via branding config */}
          <CyberParticles enabled={true} particleCount={80} connectionDistance={120} />
          
          {/* Main Header */}
          <Header />
          
          {/* Main Content */}
          <main className="relative z-10 pt-16">
            {children}
          </main>
          
          {/* Footer */}
          <footer className="relative z-10 border-t border-border bg-background/80 backdrop-blur-lg">
            <div className="container mx-auto px-4 py-8">
              <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                <p className="text-sm text-muted-foreground">
                  © {new Date().getFullYear()} Cerberus. All rights reserved.
                </p>
                <nav className="flex items-center gap-6 text-sm text-muted-foreground">
                  <a href="/privacy" className="hover:text-foreground transition-colors">
                    Privacy Policy
                  </a>
                  <a href="/terms" className="hover:text-foreground transition-colors">
                    Terms of Service
                  </a>
                  <a href="/docs" className="hover:text-foreground transition-colors">
                    Documentation
                  </a>
                </nav>
              </div>
            </div>
          </footer>
        </ThemeProvider>
      </body>
    </html>
  )
}
