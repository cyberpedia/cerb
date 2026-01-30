import Link from "next/link"
import { Shield, Target, Trophy, Users, Zap, BookOpen } from "lucide-react"

export default function Home() {
  return (
    <div className="flex flex-col items-center">
      {/* Hero Section */}
      <section className="relative w-full py-20 md:py-32 overflow-hidden">
        <div className="container mx-auto px-4 text-center relative z-10">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
            <Zap className="h-4 w-4" />
            <span>Welcome to the Future of Security Training</span>
          </div>
          
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6">
            Master Cybersecurity Through
            <span className="block mt-2 bg-gradient-to-r from-primary via-primary/80 to-primary/50 bg-clip-text text-transparent">
              Real-World Challenges
            </span>
          </h1>
          
          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
            Cerberus is an advanced security challenge platform designed to help you 
            develop practical cybersecurity skills through hands-on challenges, 
            competitions, and collaborative learning.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/auth/register"
              className="inline-flex items-center justify-center px-8 py-3 rounded-md bg-primary text-primary-foreground font-medium shadow-lg hover:bg-primary/90 transition-all duration-200 cyber-glow"
            >
              Start Learning Free
              <Shield className="ml-2 h-5 w-5" />
            </Link>
            <Link
              href="/challenges"
              className="inline-flex items-center justify-center px-8 py-3 rounded-md border border-border bg-background/50 backdrop-blur text-foreground font-medium hover:bg-accent transition-all duration-200"
            >
              Browse Challenges
              <Target className="ml-2 h-5 w-5" />
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="w-full py-20 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Why Choose Cerberus?
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Our platform provides everything you need to level up your security skills.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <FeatureCard
              icon={<Target className="h-10 w-10 text-primary" />}
              title="Hands-On Challenges"
              description="Practice with real-world security scenarios ranging from beginner to advanced levels."
            />
            <FeatureCard
              icon={<Trophy className="h-10 w-10 text-primary" />}
              title="Leaderboards & Rankings"
              description="Compete with others and climb the global rankings to prove your skills."
            />
            <FeatureCard
              icon={<Users className="h-10 w-10 text-primary" />}
              title="Team Collaboration"
              description="Form teams, share knowledge, and tackle challenges together."
            />
            <FeatureCard
              icon={<BookOpen className="h-10 w-10 text-primary" />}
              title="Learning Resources"
              description="Access tutorials, writeups, and documentation to guide your learning journey."
            />
            <FeatureCard
              icon={<Zap className="h-10 w-10 text-primary" />}
              title="Real-Time Feedback"
              description="Get instant feedback on your solutions and track your progress."
            />
            <FeatureCard
              icon={<Shield className="h-10 w-10 text-primary" />}
              title="Industry Relevant"
              description="Challenges designed to teach skills that are in-demand in the cybersecurity industry."
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="w-full py-20">
        <div className="container mx-auto px-4">
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-primary/20 via-primary/10 to-primary/20 p-8 md:p-16 text-center">
            <div className="relative z-10">
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                Ready to Start Your Journey?
              </h2>
              <p className="text-muted-foreground max-w-xl mx-auto mb-8">
                Join thousands of security professionals and enthusiasts who are 
                already learning and competing on Cerberus.
              </p>
              <Link
                href="/auth/register"
                className="inline-flex items-center justify-center px-8 py-3 rounded-md bg-background text-foreground font-medium shadow hover:bg-background/90 transition-all duration-200"
              >
                Create Free Account
              </Link>
            </div>
            
            {/* Decorative elements */}
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden">
              <div className="absolute top-10 left-10 w-20 h-20 rounded-full bg-primary/20 blur-3xl" />
              <div className="absolute bottom-10 right-10 w-32 h-32 rounded-full bg-primary/10 blur-3xl" />
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="w-full py-16 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            <StatItem value="500+" label="Challenges" />
            <StatItem value="10K+" label="Active Users" />
            <StatItem value="1M+" label="Solutions" />
            <StatItem value="50+" label="Categories" />
          </div>
        </div>
      </section>
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="group relative p-6 rounded-xl border border-border bg-background/50 backdrop-blur hover:bg-background transition-all duration-300 hover:shadow-lg hover:shadow-primary/5">
      <div className="mb-4">{icon}</div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-muted-foreground">{description}</p>
    </div>
  )
}

function StatItem({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <div className="text-3xl md:text-4xl font-bold text-primary mb-2">{value}</div>
      <div className="text-muted-foreground">{label}</div>
    </div>
  )
}
