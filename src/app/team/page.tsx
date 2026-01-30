"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Users,
  Crown,
  UserPlus,
  UserMinus,
  Copy,
  Check,
  RefreshCw,
  Shield,
  Settings,
  Trophy,
  Target,
  Clock,
  AlertTriangle,
  X,
  Mail,
  Link,
} from "lucide-react"

// Types
interface TeamMember {
  id: string
  username: string
  displayName: string
  avatar?: string
  role: "captain" | "member"
  joinedAt: string
  solved: number
  score: number
  lastActive: string
}

interface InviteCode {
  code: string
  usesRemaining: number
  expiresAt: string
  createdAt: string
}

interface Team {
  id: string
  name: string
  tag: string
  description: string
  avatar?: string
  captain: string
  createdAt: string
  score: number
  rank: number
  solved: number
  members: TeamMember[]
  inviteCodes: InviteCode[]
}

// Mock team data
const mockTeam: Team = {
  id: "1",
  name: "CyberSentinels",
  tag: "CS",
  description: "Elite cybersecurity team focused on CTF competitions and security research.",
  captain: "cyber_ninja",
  createdAt: "2024-01-01",
  score: 15420,
  rank: 1,
  solved: 47,
  members: [
    {
      id: "1",
      username: "cyber_ninja",
      displayName: "Cyber Ninja",
      role: "captain",
      joinedAt: "2024-01-01",
      solved: 28,
      score: 8750,
      lastActive: "2 mins ago",
    },
    {
      id: "2",
      username: "phantom_hacker",
      displayName: "Phantom",
      role: "member",
      joinedAt: "2024-01-05",
      solved: 22,
      score: 6200,
      lastActive: "15 mins ago",
    },
    {
      id: "3",
      username: "zero_day",
      displayName: "Zero Day",
      role: "member",
      joinedAt: "2024-01-10",
      solved: 18,
      score: 4800,
      lastActive: "1 hour ago",
    },
    {
      id: "4",
      username: "binary_beast",
      displayName: "Binary Beast",
      role: "member",
      joinedAt: "2024-01-15",
      solved: 15,
      score: 3900,
      lastActive: "3 hours ago",
    },
    {
      id: "5",
      username: "crypto_king",
      displayName: "Crypto King",
      role: "member",
      joinedAt: "2024-01-20",
      solved: 12,
      score: 3100,
      lastActive: "5 hours ago",
    },
  ],
  inviteCodes: [
    {
      code: "CS-ALPHA-2024",
      usesRemaining: 3,
      expiresAt: "2024-03-01",
      createdAt: "2024-02-01",
    },
  ],
}

// Mock current user (captain for demo)
const currentUser = {
  id: "1",
  username: "cyber_ninja",
  isCaptain: true,
}

function InviteCodeCard({
  code,
  onCopy,
  onRevoke,
  copiedCode,
}: {
  code: InviteCode
  onCopy: (code: string) => void
  onRevoke: (code: string) => void
  copiedCode: string | null
}) {
  const isExpired = new Date(code.expiresAt) < new Date()

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="p-4 rounded-xl border border-border bg-card/50 backdrop-blur-sm"
    >
      <div className="flex items-center justify-between mb-3">
        <code className="px-3 py-1 rounded-lg bg-muted font-mono text-sm">
          {code.code}
        </code>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onCopy(code.code)}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
            title="Copy code"
          >
            {copiedCode === code.code ? (
              <Check className="w-4 h-4 text-green-500" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
          {currentUser.isCaptain && (
            <button
              onClick={() => onRevoke(code.code)}
              className="p-2 rounded-lg hover:bg-destructive/10 text-destructive transition-colors"
              title="Revoke code"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Uses remaining</span>
          <span className="font-medium">{code.usesRemaining}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Expires</span>
          <span className={isExpired ? "text-destructive" : ""}>
            {isExpired ? "Expired" : code.expiresAt}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Created</span>
          <span>{code.createdAt}</span>
        </div>
      </div>
    </motion.div>
  )
}

function MemberCard({
  member,
  onKick,
}: {
  member: TeamMember
  onKick?: (member: TeamMember) => void
}) {
  const isCaptain = member.role === "captain"

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 rounded-xl border border-border bg-card/50 backdrop-blur-sm hover:border-primary/30 transition-colors"
    >
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div className="relative">
          <div className="w-14 h-14 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center border-2 border-primary/20">
            <span className="text-lg font-bold text-primary">
              {member.displayName.slice(0, 2).toUpperCase()}
            </span>
          </div>
          {isCaptain && (
            <div className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-amber-500 flex items-center justify-center shadow-lg">
              <Crown className="w-3 h-3 text-white" />
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold truncate">{member.displayName}</h3>
            {isCaptain && (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-500">
                Captain
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground mb-2">@{member.username}</p>

          <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Target className="w-3 h-3" />
              {member.solved} solved
            </span>
            <span className="flex items-center gap-1">
              <Trophy className="w-3 h-3" />
              {member.score.toLocaleString()} pts
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {member.lastActive}
            </span>
          </div>
        </div>

        {/* Actions */}
        {!isCaptain && currentUser.isCaptain && onKick && (
          <button
            onClick={() => onKick(member)}
            className="p-2 rounded-lg hover:bg-destructive/10 text-destructive transition-colors"
            title="Kick member"
          >
            <UserMinus className="w-4 h-4" />
          </button>
        )}
      </div>
    </motion.div>
  )
}

function GenerateCodeModal({
  isOpen,
  onClose,
  onGenerate,
}: {
  isOpen: boolean
  onClose: () => void
  onGenerate: (uses: number, expiresIn: number) => void
}) {
  const [uses, setUses] = useState(5)
  const [expiresIn, setExpiresIn] = useState(7)

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-md p-6 rounded-2xl border border-border bg-card shadow-xl"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">Generate Invite Code</h2>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2">
                Number of uses
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={uses}
                  onChange={(e) => setUses(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="w-12 text-center font-mono">{uses}</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Expires in (days)
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="1"
                  max="30"
                  value={expiresIn}
                  onChange={(e) => setExpiresIn(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="w-12 text-center font-mono">{expiresIn}</span>
              </div>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                onClick={onClose}
                className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onGenerate(uses, expiresIn)
                  onClose()
                }}
                className="flex-1 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                Generate
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

function KickMemberModal({
  isOpen,
  member,
  onClose,
  onConfirm,
}: {
  isOpen: boolean
  member: TeamMember | null
  onClose: () => void
  onConfirm: () => void
}) {
  if (!isOpen || !member) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-md p-6 rounded-2xl border border-destructive/30 bg-card shadow-xl"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 rounded-full bg-destructive/10">
              <AlertTriangle className="w-6 h-6 text-destructive" />
            </div>
            <h2 className="text-xl font-semibold">Kick Member</h2>
          </div>

          <p className="text-muted-foreground mb-6">
            Are you sure you want to kick{" "}
            <span className="font-semibold text-foreground">
              {member.displayName}
            </span>{" "}
            from the team? This action cannot be undone.
          </p>

          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              className="flex-1 px-4 py-2 rounded-lg bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors"
            >
              Kick Member
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

export default function TeamPage() {
  const [team, setTeam] = useState<Team>(mockTeam)
  const [copiedCode, setCopiedCode] = useState<string | null>(null)
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState(false)
  const [memberToKick, setMemberToKick] = useState<TeamMember | null>(null)
  const [activeTab, setActiveTab] = useState<"overview" | "members" | "settings">(
    "overview"
  )

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code)
    setCopiedCode(code)
    setTimeout(() => setCopiedCode(null), 2000)
  }

  const handleRevokeCode = (codeToRevoke: string) => {
    setTeam((prev) => ({
      ...prev,
      inviteCodes: prev.inviteCodes.filter((code) => code.code !== codeToRevoke),
    }))
  }

  const handleGenerateCode = (uses: number, expiresIn: number) => {
    const newCode: InviteCode = {
      code: `CS-${Math.random().toString(36).substring(2, 8).toUpperCase()}-${new Date().getFullYear()}`,
      usesRemaining: uses,
      expiresAt: new Date(Date.now() + expiresIn * 24 * 60 * 60 * 1000)
        .toISOString()
        .split("T")[0],
      createdAt: new Date().toISOString().split("T")[0],
    }

    setTeam((prev) => ({
      ...prev,
      inviteCodes: [...prev.inviteCodes, newCode],
    }))
  }

  const handleKickMember = () => {
    if (!memberToKick) return

    setTeam((prev) => ({
      ...prev,
      members: prev.members.filter((m) => m.id !== memberToKick.id),
    }))
    setMemberToKick(null)
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        {/* Team Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
            {/* Team Avatar */}
            <div className="relative">
              <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-primary to-primary/50 flex items-center justify-center border-4 border-background shadow-xl">
                <Shield className="w-12 h-12 text-primary-foreground" />
              </div>
              <div className="absolute -bottom-2 -right-2 px-3 py-1 rounded-full bg-card border-2 border-background text-sm font-bold">
                #{team.rank}
              </div>
            </div>

            {/* Team Info */}
            <div className="flex-1">
              <div className="flex flex-col md:flex-row md:items-center gap-2 md:gap-4 mb-2">
                <h1 className="text-3xl font-bold">{team.name}</h1>
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-muted text-sm">
                  <Users className="w-4 h-4" />
                  {team.members.length} members
                </span>
              </div>
              <p className="text-muted-foreground max-w-2xl mb-3">
                {team.description}
              </p>
              <div className="flex flex-wrap items-center gap-4 text-sm">
                <span className="flex items-center gap-1 text-muted-foreground">
                  <Trophy className="w-4 h-4" />
                  {team.score.toLocaleString()} points
                </span>
                <span className="flex items-center gap-1 text-muted-foreground">
                  <Target className="w-4 h-4" />
                  {team.solved} challenges solved
                </span>
                <span className="flex items-center gap-1 text-muted-foreground">
                  <Crown className="w-4 h-4" />
                  Captain: {team.captain}
                </span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-2 mb-8 border-b border-border">
          {[
            { id: "overview", label: "Overview", icon: Shield },
            { id: "members", label: "Members", icon: Users },
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
            {/* Team Stats */}
            <div className="p-6 rounded-xl border border-border bg-card/50 backdrop-blur-sm">
              <h2 className="text-lg font-semibold mb-6">Team Statistics</h2>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: "Total Score", value: team.score.toLocaleString() },
                  { label: "Challenges Solved", value: team.solved },
                  { label: "Global Rank", value: `#${team.rank}` },
                  { label: "Avg Score/Member", value: Math.round(team.score / team.members.length).toLocaleString() },
                ].map((stat) => (
                  <div
                    key={stat.label}
                    className="p-4 rounded-lg bg-muted/50 text-center"
                  >
                    <div className="text-2xl font-bold text-primary">
                      {stat.value}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {stat.label}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top Contributors */}
            <div className="p-6 rounded-xl border border-border bg-card/50 backdrop-blur-sm">
              <h2 className="text-lg font-semibold mb-6">Top Contributors</h2>
              <div className="space-y-3">
                {[...team.members]
                  .sort((a, b) => b.score - a.score)
                  .slice(0, 5)
                  .map((member, index) => (
                    <div
                      key={member.id}
                      className="flex items-center gap-3 p-3 rounded-lg bg-muted/50"
                    >
                      <div className="w-6 text-center font-bold text-muted-foreground">
                        {index + 1}
                      </div>
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
                        <span className="text-sm font-bold text-primary">
                          {member.displayName.slice(0, 2).toUpperCase()}
                        </span>
                      </div>
                      <div className="flex-1">
                        <div className="font-medium">{member.displayName}</div>
                        <div className="text-xs text-muted-foreground">
                          {member.solved} solved
                        </div>
                      </div>
                      <div className="font-mono font-bold text-primary">
                        {member.score.toLocaleString()}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === "members" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {/* Invite Codes Section (Captain Only) */}
            {currentUser.isCaptain && (
              <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-semibold">Invite Codes</h2>
                    <p className="text-sm text-muted-foreground">
                      Generate codes to invite new members to your team
                    </p>
                  </div>
                  <button
                    onClick={() => setIsGenerateModalOpen(true)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                  >
                    <UserPlus className="w-4 h-4" />
                    Generate Code
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <AnimatePresence>
                    {team.inviteCodes.map((code) => (
                      <InviteCodeCard
                        key={code.code}
                        code={code}
                        onCopy={handleCopyCode}
                        onRevoke={handleRevokeCode}
                        copiedCode={copiedCode}
                      />
                    ))}
                  </AnimatePresence>
                </div>

                {team.inviteCodes.length === 0 && (
                  <div className="p-8 text-center rounded-xl border border-dashed border-border">
                    <Mail className="w-12 h-12 mx-auto mb-3 text-muted-foreground" />
                    <p className="text-muted-foreground">
                      No active invite codes
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Generate a code to invite new members
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Members Grid */}
            <div>
              <h2 className="text-lg font-semibold mb-4">
                Team Members ({team.members.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <AnimatePresence>
                  {team.members.map((member) => (
                    <MemberCard
                      key={member.id}
                      member={member}
                      onKick={
                        currentUser.isCaptain ? setMemberToKick : undefined
                      }
                    />
                  ))}
                </AnimatePresence>
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === "settings" && currentUser.isCaptain && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-2xl"
          >
            <div className="p-6 rounded-xl border border-border bg-card/50 backdrop-blur-sm">
              <h2 className="text-lg font-semibold mb-6">Team Settings</h2>

              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Team Name
                  </label>
                  <input
                    type="text"
                    defaultValue={team.name}
                    className="w-full px-4 py-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Team Tag
                  </label>
                  <input
                    type="text"
                    defaultValue={team.tag}
                    maxLength={5}
                    className="w-32 px-4 py-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Description
                  </label>
                  <textarea
                    rows={3}
                    defaultValue={team.description}
                    className="w-full px-4 py-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                  />
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

        {activeTab === "settings" && !currentUser.isCaptain && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-12"
          >
            <Shield className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
            <h2 className="text-xl font-semibold mb-2">
              Captain Access Required
            </h2>
            <p className="text-muted-foreground">
              Only team captains can access team settings
            </p>
          </motion.div>
        )}
      </div>

      {/* Modals */}
      <GenerateCodeModal
        isOpen={isGenerateModalOpen}
        onClose={() => setIsGenerateModalOpen(false)}
        onGenerate={handleGenerateCode}
      />

      <KickMemberModal
        isOpen={!!memberToKick}
        member={memberToKick}
        onClose={() => setMemberToKick(null)}
        onConfirm={handleKickMember}
      />
    </div>
  )
}
