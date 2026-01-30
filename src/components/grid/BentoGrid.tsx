"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChallengeCard, Challenge } from "./ChallengeCard";
import { cn } from "@/lib/utils";
import { Filter, Grid3X3, LayoutGrid } from "lucide-react";

interface BentoGridProps {
  challenges: Challenge[];
  onChallengeClick?: (challenge: Challenge) => void;
  className?: string;
  categories?: string[];
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: [0.4, 0, 0.2, 1],
    },
  },
};

export function BentoGrid({
  challenges,
  onChallengeClick,
  className,
  categories: customCategories,
}: BentoGridProps) {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedDifficulty, setSelectedDifficulty] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"masonry" | "compact">("masonry");

  // Extract unique categories from challenges
  const categories = useMemo(() => {
    if (customCategories) return customCategories;
    const uniqueCategories = new Set(challenges.map((c) => c.category));
    return Array.from(uniqueCategories).sort();
  }, [challenges, customCategories]);

  const difficulties = ["easy", "medium", "hard", "insane"];

  // Filter challenges
  const filteredChallenges = useMemo(() => {
    return challenges.filter((challenge) => {
      const categoryMatch = !selectedCategory || challenge.category === selectedCategory;
      const difficultyMatch = !selectedDifficulty || challenge.difficulty === selectedDifficulty;
      return categoryMatch && difficultyMatch;
    });
  }, [challenges, selectedCategory, selectedDifficulty]);

  // Group challenges by category for organization
  const groupedChallenges = useMemo(() => {
    const grouped: Record<string, Challenge[]> = {};
    filteredChallenges.forEach((challenge) => {
      if (!grouped[challenge.category]) {
        grouped[challenge.category] = [];
      }
      grouped[challenge.category].push(challenge);
    });
    return grouped;
  }, [filteredChallenges]);

  // Calculate grid columns based on challenge layout config
  const getGridClass = () => {
    if (viewMode === "compact") {
      return "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4";
    }
    // Masonry mode with dynamic spans
    return "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 auto-rows-min";
  };

  return (
    <div className={cn("space-y-6", className)}>
      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium text-muted-foreground">Filters:</span>
        </div>

        <div className="flex flex-wrap gap-3 items-center">
          {/* Category Filters */}
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => setSelectedCategory(null)}
              className={cn(
                "px-3 py-1.5 text-xs font-medium rounded-full transition-all duration-200",
                "border border-white/10 hover:border-white/20",
                selectedCategory === null
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-white/5 text-muted-foreground hover:bg-white/10"
              )}
            >
              All
            </button>
            {categories.map((category) => (
              <button
                key={category}
                onClick={() =>
                  setSelectedCategory(category === selectedCategory ? null : category)
                }
                className={cn(
                  "px-3 py-1.5 text-xs font-medium rounded-full transition-all duration-200",
                  "border border-white/10 hover:border-white/20 capitalize",
                  selectedCategory === category
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-white/5 text-muted-foreground hover:bg-white/10"
                )}
              >
                {category}
              </button>
            ))}
          </div>

          <div className="w-px h-6 bg-white/10 hidden sm:block" />

          {/* Difficulty Filters */}
          <div className="flex flex-wrap gap-1.5">
            {difficulties.map((difficulty) => (
              <button
                key={difficulty}
                onClick={() =>
                  setSelectedDifficulty(difficulty === selectedDifficulty ? null : difficulty)
                }
                className={cn(
                  "px-2.5 py-1 text-xs font-medium rounded-full transition-all duration-200 capitalize",
                  "border",
                  selectedDifficulty === difficulty
                    ? difficulty === "easy"
                      ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/50"
                      : difficulty === "medium"
                      ? "bg-amber-500/20 text-amber-400 border-amber-500/50"
                      : difficulty === "hard"
                      ? "bg-rose-500/20 text-rose-400 border-rose-500/50"
                      : "bg-purple-500/20 text-purple-400 border-purple-500/50"
                    : "bg-white/5 text-muted-foreground border-white/10 hover:bg-white/10"
                )}
              >
                {difficulty}
              </button>
            ))}
          </div>

          <div className="w-px h-6 bg-white/10 hidden sm:block" />

          {/* View Mode Toggle */}
          <div className="flex items-center gap-1 bg-white/5 rounded-lg p-1 border border-white/10">
            <button
              onClick={() => setViewMode("masonry")}
              className={cn(
                "p-1.5 rounded-md transition-all duration-200",
                viewMode === "masonry"
                  ? "bg-white/10 text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
              title="Masonry View"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode("compact")}
              className={cn(
                "p-1.5 rounded-md transition-all duration-200",
                viewMode === "compact"
                  ? "bg-white/10 text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
              title="Compact View"
            >
              <Grid3X3 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Results Count */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Showing {filteredChallenges.length} of {challenges.length} challenges
        </span>
        {(selectedCategory || selectedDifficulty) && (
          <button
            onClick={() => {
              setSelectedCategory(null);
              setSelectedDifficulty(null);
            }}
            className="text-primary hover:text-primary/80 transition-colors"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Challenges Grid */}
      <AnimatePresence mode="wait">
        <motion.div
          key={`${selectedCategory}-${selectedDifficulty}-${viewMode}`}
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          exit={{ opacity: 0 }}
          className={cn(
            "grid gap-4",
            getGridClass()
          )}
        >
          {filteredChallenges.map((challenge) => (
            <motion.div
              key={challenge.id}
              variants={itemVariants}
              layout
              className={cn(
                // Apply col-span and row-span from layout config
                challenge.ui_layout_config?.colSpan === 2 && "sm:col-span-2",
                challenge.ui_layout_config?.rowSpan === 2 && "row-span-2",
                viewMode === "compact" && "col-span-1 !row-span-1"
              )}
            >
              <ChallengeCard
                challenge={challenge}
                onClick={onChallengeClick}
                className={cn(
                  "h-full min-h-[180px]",
                  challenge.ui_layout_config?.rowSpan === 2 && "min-h-[380px]"
                )}
              />
            </motion.div>
          ))}
        </motion.div>
      </AnimatePresence>

      {/* Empty State */}
      {filteredChallenges.length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-16 text-center"
        >
          <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
            <Filter className="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            No challenges found
          </h3>
          <p className="text-sm text-muted-foreground max-w-sm">
            Try adjusting your filters or clear them to see all available challenges.
          </p>
          <button
            onClick={() => {
              setSelectedCategory(null);
              setSelectedDifficulty(null);
            }}
            className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            Clear all filters
          </button>
        </motion.div>
      )}
    </div>
  );
}

export default BentoGrid;
