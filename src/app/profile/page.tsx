"use client"

import { useState } from "react"
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from "recharts"
import { motion } from "framer-motion"
import {
  User,
  Shield,
  Trophy,
  Target,
  Zap,
  Award,
  Star,
  Lock,
  Code,
  Binary,
  Globe,
  Server,
  Clock,
  TrendingUp,
  Users,
  Settings,
  Copy,
  Check,
} from "lucide-react"

// Types
interface Skill {
  subject: string
  value: number
  fullMark: number
}

interface Badge {
  id: string
  name: string
  description: string
  icon: React.ReactNode
  rarity: "common" | "rare" | "epic" | "legendary"
  unlockedAt?: string
  locked?: boolean
}

interface UserProfile {
  id: string
  username: string
  displayName: string
  avatar?: string
  team?: string
  rank: number
  score: number
  solved: number
  streak: number
  joinedAt: string
}

// Mock user data
const mockUser: UserProfile = {
  id: "1",
  username: "cyber_ninja",
  displayName: "Cyber Ninja",
  team: "CyberSentinels",
  rank: 42,
  score: 8750,
  solved: 28,
  streak: 7,
  joinedAt: "2024-01-15",
}

// Skill data for radar chart
const skillData: Skill[] = [
  { subject: "Web Exploitation", value: 85, fullMark: 100 },
  { subject: "Cryptography", value: 70, fullMark: 100 },
  { subject: "Reverse Eng", value: 65, fullMark: 100 },
  { subject: "Forensics", value: 80, fullMark: 100 },
  { subject: "Binary Exploit", value: 55, fullMark: 100 },
  { subject: "OSINT", value: 90, fullMark: 100 },
]

// Badge data
const badges: Badge[] = [
  {
    id: "1",
    name: "First Blood",
    description: "Solve your first challenge",
    icon: <Target className="w-6 h-6" />,
    rarity: "common",
    unlockedAt: "2024-01-15",
  },
  {
    id: "2",
    name: "Speed Demon",
    description: "Solve 5 challenges in under 1 hour",
    icon: <Zap className="w-6 h-6" />,
    rarity: "rare",
    unlockedAt: "2024-01-20",
  },
  {
    id: "3",
    name: "Web Warrior",
    description: "Solve 10 web exploitation challenges",
    icon: <Globe className="w-6 h-6" />,
    rarity: "rare",
    unlockedAt: "2024-01-25",
  },
  {
    id: "4",
    name: "Crypto Master",
    description: "Solve 15 cryptography challenges",
    icon: <Lock className="w-6 h-6" />,
    rarity: "epic",
    unlockedAt: "2024-02-01",
  },
  {
    id: "5",
    name: "Code Breaker",
    description: "Reverse engineer 5 binaries",
    icon: <Code className="w-6 h-6" />,
    rarity: "epic",
    locked: true,
  },
  {
    id: "6",
    name: "Binary Beast",
    description: "Solve 10 binary exploitation challenges",
    icon: <Binary className="w-6 h-6" />,
    rarity: "legendary",
    locked: true,
  },
  {
    id: "7",
    name: "Server Sage",
    description: "Compromise 5 different server types",
    icon: <Server className="w-6 h-6" />,
    rarity: "legendary",
    locked: true,
  },
  {
    id: "8",
    name: "Team Player",
    description: "Contribute to team score 10 times",
    icon: <Users className="w-6 h-6" />,
    rarity: "common",
    unlockedAt: "2024-01-18",
  },
  {
    id: "9",
    name: "Week Streak",
    description: "Solve at least one challenge for 7 days",
    icon: <Clock className="w-6 h-6" />,
    rarity: "rare",
    unlockedAt: "2024-01-28",
  },
  {
    id: "10",
    name: "Rising Star",
    description: "Reach top 50 on the leaderboard",
    icon: <Star className="w-6 h-6" />,
    rarity: "epic",
    unlockedAt: "2024-02-05",
  },
  {
    id: "11",
    name: "Perfectionist",
    description: "Solve a challenge on first attempt",
    icon: <Award className="w-6 h-6" />,
    rarity: "rare",
    unlockedAt: "2024-01-22",
  },
  {
    id: "12",
    name: "Legend",
    description: "Reach #1 on the leaderboard",
    icon: <Trophy className="w-6 h-6" />,
    rarity: "legendary",
    locked: true,
  },
]

const rarityColors = {
  common: {
    bg: "from-gray-500/20 to-gray-500/5",
    border: "border-gray-500/30",
    text: "text-gray-400",
    glow: "shadow-gray-500/20",
  },
  rare: {
    bg: "from-blue-500/20 to-blue-500/5",
    border: "border-blue-500/30",
    text: "text-blue-400",
    glow: "shadow-blue-500/20",
  },
  epic: {
    bg: "from-purple-500/20 to-purple-500/5",
    border: "border-purple-500/30",
    text: "text-purple-400",
    glow: "shadow-purple-500/20",
  },
  legendary: {
    bg: "from-amber-500/20 to-amber-500/5",
    border: "border-amber-500/30",
    text: "text-amber-400",
    glow: "shadow-amber-500/20",
  },
}

const rarityLabels = {
  common: "Common",
  rare: "Rare",
  epic: "Epic",
  legendary: "Legendary",
}

function BadgeHexagon({ badge, index }: { badge: Badge; index: number }) {
  const colors = rarityColors[badge.rarity]

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.05 }}
      className="group relative"
    >
      <div
        className={`
          relative w-24 h-28 mx-auto
          flex flex-col items-center justify-center
          bg-gradient-to-br ${colors.bg}
          border ${colors.border}
          rounded-2xl
          transition-all duration-300
          ${badge.locked ? "opacity-50 grayscale" : `hover:shadow-lg ${colors.glow} hover:scale-105`}
        `}
        style={{
          clipPath:
            "polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)",
        }}
      >
        <div className={`${colors.text} mb-1`}>
          {badge.locked ? <Lock className="w-5 h-5" /> : badge.icon}
        </div>
        <span className="text-[8px] font-bold text-center px-2 leading-tight">
          {badge.name}
        </span>
      </div>

      {/* Tooltip */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-3 rounded-lg bg-card border border-border shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
        <div className="flex items-center gap-2 mb-1">
          <span className={`${colors.text}`}>{badge.icon}</span>
          <span className="font-semibold text-sm">{badge.name}</span>
        </div>
        <p className="text-xs text-muted-foreground mb-2">
          {badge.description}
        </p>
        <div className="flex items-center justify-between">
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full bg-gradient-to-r ${colors.bg} ${colors.text}`}
          >
            {rarityLabels[badge.rarity]}
          </span>
          {badge.unlockedAt && (
            <span className="text-xs text-muted-foreground">
              {badge.unlockedAt}
            </span>
          )}
        </div>
      </div>
    </motion.div>
  )
}

export default function ProfilePage() {
  const [activeTab, setActiveTab] = useState<"overview" | "badges" | "settings">(
    "overview"
  )
  const [copied, setCopied] = useState(false)

  const handleCopyUsername = () => {
    navigator.clipboard.writeText(mockUser.username)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const unlockedBadges = badges.filter((b) => !b.locked)
  const lockedBadges = badges.filter((b) => b.locked)

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        {/* Profile Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
            {/* Avatar */}
            <div className="relative">
              <div className="w-24 h-24 rounded-full bg-gradient-to-br from-primary to-primary/50 flex items-center justify-center border-4 border-background shadow-xl">
                <User className="w-12 h-12 text-primary-foreground" />
              </div>
              <div className="absolute -bottom-2 -right-2 w-8 h-8 rounded-full bg-card border-2 border-background flex items-center justify-center">
                <Shield className="w-4 h-4 text-primary" />
              </div>
            </div>

            {/* User Info */}
            <div className="flex-1">
              <div className="flex flex-col md:flex-row md:items-center gap-2 md:gap-4 mb-2">
                <h1 className="text-3xl font-bold">{mockUser.displayName}</h1>
                <button
                  onClick={handleCopyUsername}
                  className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-muted text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  @{mockUser.username}
                  {copied ? (
                    <Check className="w-3 h-3 text-green-500" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                </button>
              </div>
              <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                {mockUser.team && (
                  <span className="flex items-center gap-1">
                    <Users className="w-4 h-4" />
                    {mockUser.team}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Trophy className="w-4 h-4" />
                  Rank #{mockUser.rank}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  Joined {mockUser.joinedAt}
                </span>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="flex gap-4">
              <div className="text-center px-4 py-2 rounded-xl bg-card border border-border">
                <div className="text-2xl font-bold text-primary">
                  {mockUser.score.toLocaleString()}
                </div>
                <div className="text-xs text-muted-foreground">Score</div>
              </div>
              <div className="text-center px-4 py-2 rounded-xl bg-card border border-border">
                <div className="text-2xl font-bold text-primary">
                  {mockUser.solved}
                </div>
                <div className="text-xs text-muted-foreground">Solved</div>
              </div>
              <div className="text-center px-4 py-2 rounded-xl bg-card border border-border">
                <div className="text-2xl font-bold text-primary">
                  {mockUser.streak}
                </div>
                <div className="text-xs text-muted-foreground">Day Streak</div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-2 mb-8 border-b border-border">
          {[
            { id: "overview", label: "Overview", icon: User },
            { id: "badges", label: "Badges", icon: Award },
            { id: "settings", label: "Settings", icon: Settings },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`
                flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors
                ${activeTab === tab.id ? "text-primary border-b-2 border-primary" : "text-muted-foreground hover:text-foreground"}
              `}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === "overview" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-8"
          >
            {/* Skills Radar Chart */}
            <div className="p-6 rounded-xl border border-border bg-card/50 backdrop-blur-sm">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Target className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold">Skill Distribution</h2>
                  <p className="text-sm text-muted-foreground">
                    Your performance across different categories
                  </p>
                </div>
              </div>

              <div className="h-[350px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={skillData}>
                    <PolarGrid stroke="hsl(var(--border))" />
                    <PolarAngleAxis
                      dataKey="subject"
                      tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                    />
                    <PolarRadiusAxis
                      angle={90}
                      domain={[0, 100]}
                      tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }}
                      tickCount={6}
                    />
                    <Radar
                      name="Skills"
                      dataKey="value"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      fill="hsl(var(--primary))"
                      fillOpacity={0.3}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px",
                      }}
                      labelStyle={{ color: "hsl(var(--foreground))" }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="p-6 rounded-xl border border-border bg-card/50 backdrop-blur-sm">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-primary/10">
                  <TrendingUp className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold">Recent Activity</h2>
                  <p className="text-sm text-muted-foreground">
                    Your latest challenge solves
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                {[
                  {
                    challenge: "SQL Injection Master",
                    category: "Web Exploitation",
                    points: 500,
                    time: "2 hours ago",
                  },
                  {
                    challenge: "Crypto Vault",
                    category: "Cryptography",
                    points: 750,
                    time: "5 hours ago",
                  },
                  {
                    challenge: "Hidden Message",
                    category: "Forensics",
                    points: 300,
                    time: "Yesterday",
                  },
                  {
                    challenge: "Reverse Me",
                    category: "Reverse Engineering",
                    points: 600,
                    time: "2 days ago",
                  },
                ].map((activity, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="flex items-center gap-4 p-4 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
                  >
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <Target className="w-5 h-5 text-primary" />
                    </div>
                    <div className="flex-1">
                      <div className="font-medium">{activity.challenge}</div>
                      <div className="text-sm text-muted-foreground">
                        {activity.category}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-mono font-bold text-primary">
                        +{activity.points}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {activity.time}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === "badges" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {/* Badge Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              {[
                { label: "Total Badges", value: badges.length, icon: Award },
                { label: "Unlocked", value: unlockedBadges.length, icon: Trophy },
                { label: "Locked", value: lockedBadges.length, icon: Lock },
                { label: "Legendary", value: 0, icon: Star },
              ].map((stat, index) => (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="p-4 rounded-xl border border-border bg-card/50 text-center"
                >
                  <stat.icon className="w-6 h-6 mx-auto mb-2 text-primary" />
                  <div className="text-2xl font-bold">{stat.value}</div>
                  <div className="text-xs text-muted-foreground">{stat.label}</div>
                </motion.div>
              ))}
            </div>

            {/* Unlocked Badges */}
            <div className="mb-8">
              <h3 className="text-lg font-semibold mb-4">Unlocked Badges</h3>
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-4">
                {unlockedBadges.map((badge, index) => (
                  <BadgeHexagon key={badge.id} badge={badge} index={index} />
                ))}
              </div>
            </div>

            {/* Locked Badges */}
            <div>
              <h3 className="text-lg font-semibold mb-4 text-muted-foreground">
                Locked Badges
              </h3>
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-4">
                {lockedBadges.map((badge, index) => (
                  <BadgeHexagon
                    key={badge.id}
                    badge={badge}
                    index={index + unlockedBadges.length}
                  />
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === "settings" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-2xl"
          >
            <div className="p-6 rounded-xl border border-border bg-card/50 backdrop-blur-sm">
              <h2 className="text-lg font-semibold mb-6">Profile Settings</h2>

              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Display Name
                  </label>
                  <input
                    type="text"
                    defaultValue={mockUser.displayName}
                    className="w-full px-4 py-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Bio</label>
                  <textarea
                    rows={3}
                    placeholder="Tell us about yourself..."
                    className="w-full px-4 py-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Profile Visibility
                  </label>
                  <select className="w-full px-4 py-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary">
                    <option value="public">Public</option>
                    <option value="team">Team Only</option>
                    <option value="private">Private</option>
                  </select>
                </div>

                <div className="pt-4 border-t border-border">
                  <button className="px-6 py-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors">
                    Save Changes
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}
