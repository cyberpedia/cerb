"use client";

import { motion } from "framer-motion";
import { Lock, Unlock, Trophy, Server, Terminal, Brain, FileSearch, Shield, Globe, Cpu, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

export interface Challenge {
  id: string;
  title: string;
  description: string;
  points: number;
  category: string;
  difficulty: "easy" | "medium" | "hard" | "insane";
  subtype: string;
  is_active: boolean;
  is_dynamic: boolean;
  max_attempts: number | null;
  ui_layout_config?: {
    colSpan?: number;
    rowSpan?: number;
    featured?: boolean;
  } | null;
  connection_info?: {
    host?: string;
    port?: number;
    type?: string;
  } | null;
  solved?: boolean;
  solvesCount?: number;
  isLocked?: boolean;
  missingPrereqs?: string[];
}

interface ChallengeCardProps {
  challenge: Challenge;
  onClick?: (challenge: Challenge) => void;
  className?: string;
}

const categoryIcons: Record<string, React.ReactNode> = {
  web: <Globe className="w-5 h-5" />,
  crypto: <Shield className="w-5 h-5" />,
  pwn: <Terminal className="w-5 h-5" />,
  reverse: <Cpu className="w-5 h-5" />,
  forensics: <FileSearch className="w-5 h-5" />,
  misc: <Zap className="w-5 h-5" />,
  blockchain: <Server className="w-5 h-5" />,
  ai: <Brain className="w-5 h-5" />,
  cloud: <Server className="w-5 h-5" />,
};

const difficultyColors: Record<string, string> = {
  easy: "text-emerald-400 border-emerald-400/30 bg-emerald-400/10",
  medium: "text-amber-400 border-amber-400/30 bg-amber-400/10",
  hard: "text-rose-400 border-rose-400/30 bg-rose-400/10",
  insane: "text-purple-400 border-purple-400/30 bg-purple-400/10",
};

const categoryColors: Record<string, string> = {
  web: "from-blue-500/20 to-cyan-500/20",
  crypto: "from-emerald-500/20 to-teal-500/20",
  pwn: "from-red-500/20 to-orange-500/20",
  reverse: "from-purple-500/20 to-pink-500/20",
  forensics: "from-yellow-500/20 to-amber-500/20",
  misc: "from-gray-500/20 to-slate-500/20",
  blockchain: "from-orange-500/20 to-yellow-500/20",
  ai: "from-violet-500/20 to-purple-500/20",
  cloud: "from-sky-500/20 to-blue-500/20",
};

export function ChallengeCard({ challenge, onClick, className }: ChallengeCardProps) {
  const {
    title,
    description,
    points,
    category,
    difficulty,
    is_dynamic,
    solved,
    isLocked,
    missingPrereqs,
  } = challenge;

  const colSpan = challenge.ui_layout_config?.colSpan || 1;
  const rowSpan = challenge.ui_layout_config?.rowSpan || 1;
  const isFeatured = challenge.ui_layout_config?.featured || false;

  const handleClick = () => {
    if (!isLocked && onClick) {
      onClick(challenge);
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      whileHover={!isLocked ? { scale: 1.02, y: -4 } : {}}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className={cn(
        "relative group cursor-pointer overflow-hidden rounded-xl",
        "border border-white/10 backdrop-blur-md",
        "bg-gradient-to-br from-white/5 to-white/[0.02]",
        "transition-all duration-300",
        isLocked && "cursor-not-allowed opacity-70",
        solved && "border-emerald-500/30",
        isFeatured && "ring-1 ring-primary/20",
        className
      )}
      style={{
        gridColumn: `span ${colSpan}`,
        gridRow: `span ${rowSpan}`,
      }}
      onClick={handleClick}
    >
      {/* Glass Background Gradient */}
      <div
        className={cn(
          "absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500",
          "bg-gradient-to-br",
          categoryColors[category.toLowerCase()] || categoryColors.misc
        )}
      />

      {/* Glow Effect */}
      {!isLocked && (
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000" />
        </div>
      )}

      {/* Border Glow on Hover */}
      <div
        className={cn(
          "absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300",
          "bg-gradient-to-r from-primary/20 via-purple-500/20 to-primary/20",
          "blur-sm",
          isLocked && "hidden"
        )}
      />

      {/* Content Container */}
      <div className="relative z-10 p-5 h-full flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "p-2 rounded-lg bg-white/5 border border-white/10",
                "group-hover:bg-white/10 group-hover:border-white/20 transition-colors",
                solved && "bg-emerald-500/20 border-emerald-500/30"
              )}
            >
              {categoryIcons[category.toLowerCase()] || categoryIcons.misc}
            </div>
            <div>
              <span
                className={cn(
                  "text-xs font-medium px-2 py-0.5 rounded-full border",
                  difficultyColors[difficulty]
                )}
              >
                {difficulty}
              </span>
            </div>
          </div>

          {/* Status Icons */}
          <div className="flex items-center gap-1.5">
            {is_dynamic && (
              <Server className="w-4 h-4 text-blue-400" title="Dynamic Challenge" />
            )}
            {solved && (
              <Trophy className="w-4 h-4 text-emerald-400" title="Solved" />
            )}
            {isLocked ? (
              <Lock className="w-4 h-4 text-rose-400" title="Locked" />
            ) : (
              <Unlock className="w-4 h-4 text-emerald-400/50 opacity-0 group-hover:opacity-100 transition-opacity" />
            )}
          </div>
        </div>

        {/* Title */}
        <h3
          className={cn(
            "font-semibold text-lg mb-2 line-clamp-2",
            "text-foreground group-hover:text-primary transition-colors",
            isLocked && "text-muted-foreground"
          )}
        >
          {title}
        </h3>

        {/* Description */}
        <p className="text-sm text-muted-foreground line-clamp-2 mb-4 flex-grow">
          {description}
        </p>

        {/* Footer */}
        <div className="flex items-center justify-between mt-auto pt-3 border-t border-white/5">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground uppercase tracking-wider">
              {category}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Trophy className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-sm font-medium text-foreground">{points}</span>
          </div>
        </div>

        {/* Lock Overlay */}
        {isLocked && (
          <div className="absolute inset-0 bg-background/60 backdrop-blur-[2px] flex flex-col items-center justify-center z-20">
            <Lock className="w-8 h-8 text-rose-400 mb-2" />
            <p className="text-xs text-muted-foreground text-center px-4">
              Complete required challenges to unlock
            </p>
            {missingPrereqs && missingPrereqs.length > 0 && (
              <div className="mt-2 text-xs text-rose-400/80 text-center">
                Requires: {missingPrereqs.join(", ")}
              </div>
            )}
          </div>
        )}

        {/* Solved Badge */}
        {solved && (
          <div className="absolute top-0 right-0 w-16 h-16 overflow-hidden">
            <div className="absolute top-2 right-[-35px] w-[100px] bg-emerald-500 text-white text-xs font-bold py-1 text-center rotate-45">
              SOLVED
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default ChallengeCard;
