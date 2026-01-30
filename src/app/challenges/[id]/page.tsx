"use client";

import { useEffect, useState, useCallback, FormEvent, ReactNode } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowLeft,
  Trophy,
  Clock,
  Users,
  Download,
  Flag,
  Terminal,
  Server,
  Shield,
  AlertCircle,
  CheckCircle2,
  XCircle,
  FileText,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { TerminalDrawer } from "@/components/workspace/TerminalDrawer";

// Types
interface Challenge {
  id: string;
  title: string;
  description: string;
  points: number;
  category: string;
  difficulty: "easy" | "medium" | "hard" | "insane";
  subtype: string;
  is_dynamic: boolean;
  max_attempts: number | null;
  attempt_count: number;
  connection_info?: {
    host?: string;
    port?: number;
    type?: string;
    container_id?: string;
  } | null;
  solved_at?: string | null;
  files?: ChallengeFile[];
}

interface ChallengeFile {
  id: string;
  filename: string;
  url: string;
  size?: number;
}

interface SubmissionResult {
  result: "correct" | "incorrect" | "already_solved" | "error";
  message?: string;
  points?: number;
  attempts_remaining?: number;
}

// Difficulty colors
const difficultyColors: Record<string, string> = {
  easy: "text-emerald-400 border-emerald-400/30 bg-emerald-400/10",
  medium: "text-amber-400 border-amber-400/30 bg-amber-400/10",
  hard: "text-rose-400 border-rose-400/30 bg-rose-400/10",
  insane: "text-purple-400 border-purple-400/30 bg-purple-400/10",
};

const categoryIcons: Record<string, ReactNode> = {
  web: <ExternalLink className="w-5 h-5" />,
  crypto: <Shield className="w-5 h-5" />,
  pwn: <Terminal className="w-5 h-5" />,
  reverse: <FileText className="w-5 h-5" />,
  forensics: <FileText className="w-5 h-5" />,
  misc: <Terminal className="w-5 h-5" />,
  blockchain: <Server className="w-5 h-5" />,
  ai: <Terminal className="w-5 h-5" />,
  cloud: <Server className="w-5 h-5" />,
};

export default function ChallengeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const challengeId = params.id as string;

  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [flagInput, setFlagInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionResult, setSubmissionResult] = useState<SubmissionResult | null>(null);
  const [isTerminalOpen, setIsTerminalOpen] = useState(false);

  // Fetch challenge data
  useEffect(() => {
    const fetchChallenge = async () => {
      try {
        const token = localStorage.getItem("token");
        const response = await fetch(`/api/challenges/${challengeId}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error("Challenge not found");
          }
          throw new Error("Failed to load challenge");
        }

        const data = await response.json();
        setChallenge(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setIsLoading(false);
      }
    };

    if (challengeId) {
      fetchChallenge();
    }
  }, [challengeId]);

  // Handle flag submission
  const handleSubmitFlag = useCallback(async (e: FormEvent) => {
    e.preventDefault();
    if (!flagInput.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setSubmissionResult(null);

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/api/challenges/${challengeId}/submit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify({ flag: flagInput.trim() }),
      });

      const result = await response.json();
      setSubmissionResult(result);

      if (result.result === "correct") {
        setFlagInput("");
        // Refresh challenge data to show solved state
        setChallenge((prev: Challenge | null) =>
          prev
            ? {
                ...prev,
                solved_at: new Date().toISOString(),
              }
            : null
        );
      }
    } catch (err) {
      setSubmissionResult({
        result: "error",
        message: "Failed to submit flag. Please try again.",
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [challengeId, flagInput, isSubmitting]);

  // Handle file download
  const handleDownload = useCallback((file: ChallengeFile) => {
    const link = document.createElement("a");
    link.href = file.url;
    link.download = file.filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, []);

  // Format file size
  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return "";
    const units = ["B", "KB", "MB", "GB"];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
          <span className="text-muted-foreground">Loading challenge...</span>
        </div>
      </div>
    );
  }

  if (error || !challenge) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <AlertCircle className="w-12 h-12 text-rose-400" />
        <h1 className="text-xl font-semibold">{error || "Challenge not found"}</h1>
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Challenges
        </button>
      </div>
    );
  }

  const isSolved = !!challenge.solved_at;
  const attemptsRemaining = challenge.max_attempts
    ? challenge.max_attempts - challenge.attempt_count
    : null;

  return (
    <div className="min-h-screen pb-[400px]">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-background/80 backdrop-blur-md border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push("/")}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-white/5 rounded-md transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>

            <div className="flex-1">
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-bold">{challenge.title}</h1>
                {isSolved && (
                  <span className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-emerald-400 bg-emerald-400/10 border border-emerald-400/30 rounded-full">
                    <CheckCircle2 className="w-3 h-3" />
                    Solved
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span
                  className={cn(
                    "text-xs font-medium px-2 py-0.5 rounded-full border",
                    difficultyColors[challenge.difficulty]
                  )}
                >
                  {challenge.difficulty}
                </span>
                <span className="text-sm text-muted-foreground">{challenge.category}</span>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-sm">
                <Trophy className="w-4 h-4 text-amber-400" />
                <span className="font-medium">{challenge.points} pts</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Description */}
          <div className="lg:col-span-2 space-y-6">
            {/* Challenge Description */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white/5 border border-white/10 rounded-xl p-6"
            >
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary" />
                Description
              </h2>
              <div className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {challenge.description}
                </ReactMarkdown>
              </div>
            </motion.div>

            {/* Files Section */}
            {challenge.files && challenge.files.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-white/5 border border-white/10 rounded-xl p-6"
              >
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Download className="w-5 h-5 text-primary" />
                  Files
                </h2>
                <div className="space-y-2">
                  {challenge.files.map((file) => (
                    <button
                      key={file.id}
                      onClick={() => handleDownload(file)}
                      className="w-full flex items-center justify-between p-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-colors group"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded-md">
                          <Download className="w-4 h-4 text-primary" />
                        </div>
                        <div className="text-left">
                          <p className="font-medium text-sm group-hover:text-primary transition-colors">
                            {file.filename}
                          </p>
                          {file.size && (
                            <p className="text-xs text-muted-foreground">
                              {formatFileSize(file.size)}
                            </p>
                          )}
                        </div>
                      </div>
                      <ArrowLeft className="w-4 h-4 text-muted-foreground rotate-[-90deg] group-hover:translate-x-1 transition-transform" />
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Connection Info */}
            {challenge.connection_info && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-white/5 border border-white/10 rounded-xl p-6"
              >
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Server className="w-5 h-5 text-primary" />
                  Connection Info
                </h2>
                <div className="space-y-3">
                  {challenge.connection_info.host && (
                    <div className="flex items-center justify-between p-3 bg-black/30 rounded-lg">
                      <span className="text-sm text-muted-foreground">Host</span>
                      <code className="text-sm font-mono text-emerald-400">
                        {challenge.connection_info.host}
                      </code>
                    </div>
                  )}
                  {challenge.connection_info.port && (
                    <div className="flex items-center justify-between p-3 bg-black/30 rounded-lg">
                      <span className="text-sm text-muted-foreground">Port</span>
                      <code className="text-sm font-mono text-emerald-400">
                        {challenge.connection_info.port}
                      </code>
                    </div>
                  )}
                  {challenge.connection_info.type && (
                    <div className="flex items-center justify-between p-3 bg-black/30 rounded-lg">
                      <span className="text-sm text-muted-foreground">Type</span>
                      <span className="text-sm font-medium">
                        {challenge.connection_info.type}
                      </span>
                    </div>
                  )}
                </div>

                {/* Terminal Button */}
                {challenge.is_dynamic && challenge.connection_info.container_id && (
                  <button
                    onClick={() => setIsTerminalOpen(true)}
                    className="mt-4 w-full flex items-center justify-center gap-2 p-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                  >
                    <Terminal className="w-4 h-4" />
                    Open Terminal
                  </button>
                )}
              </motion.div>
            )}
          </div>

          {/* Right Column - Flag Submission */}
          <div className="space-y-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="bg-white/5 border border-white/10 rounded-xl p-6 sticky top-24"
            >
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Flag className="w-5 h-5 text-primary" />
                Submit Flag
              </h2>

              {isSolved ? (
                <div className="text-center py-6">
                  <div className="w-16 h-16 mx-auto mb-4 bg-emerald-500/20 rounded-full flex items-center justify-center">
                    <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                  </div>
                  <p className="text-emerald-400 font-medium">Challenge Solved!</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    You earned {challenge.points} points
                  </p>
                </div>
              ) : (
                <form onSubmit={handleSubmitFlag} className="space-y-4">
                  <div>
                    <input
                      type="text"
                      value={flagInput}
                      onChange={(e) => setFlagInput(e.target.value)}
                      placeholder="flag{...}"
                      className={cn(
                        "w-full px-4 py-3 bg-black/30 border rounded-lg",
                        "text-sm font-mono",
                        "placeholder:text-muted-foreground/50",
                        "focus:outline-none focus:ring-2 focus:ring-primary/50",
                        "transition-all",
                        submissionResult?.result === "incorrect"
                          ? "border-rose-500/50 focus:border-rose-500"
                          : submissionResult?.result === "correct"
                          ? "border-emerald-500/50 focus:border-emerald-500"
                          : "border-white/10 focus:border-primary"
                      )}
                      disabled={isSubmitting}
                    />
                  </div>

                  {/* Submission Result */}
                  {submissionResult && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={cn(
                        "p-3 rounded-lg text-sm flex items-start gap-2",
                        submissionResult.result === "correct"
                          ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                          : submissionResult.result === "incorrect"
                          ? "bg-rose-500/10 border border-rose-500/30 text-rose-400"
                          : "bg-amber-500/10 border border-amber-500/30 text-amber-400"
                      )}
                    >
                      {submissionResult.result === "correct" ? (
                        <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
                      ) : submissionResult.result === "incorrect" ? (
                        <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
                      ) : (
                        <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                      )}
                      <div>
                        <p className="font-medium">
                          {submissionResult.result === "correct"
                            ? "Correct!"
                            : submissionResult.result === "incorrect"
                            ? "Incorrect flag"
                            : submissionResult.result === "already_solved"
                            ? "Already solved"
                            : "Error"}
                        </p>
                        {submissionResult.message && (
                          <p className="text-xs mt-0.5 opacity-80">
                            {submissionResult.message}
                          </p>
                        )}
                        {submissionResult.attempts_remaining !== undefined && (
                          <p className="text-xs mt-0.5 opacity-80">
                            {submissionResult.attempts_remaining} attempts remaining
                          </p>
                        )}
                      </div>
                    </motion.div>
                  )}

                  <button
                    type="submit"
                    disabled={!flagInput.trim() || isSubmitting}
                    className={cn(
                      "w-full py-3 px-4 rounded-lg font-medium",
                      "bg-primary text-primary-foreground",
                      "hover:bg-primary/90",
                      "disabled:opacity-50 disabled:cursor-not-allowed",
                      "transition-all",
                      "flex items-center justify-center gap-2"
                    )}
                  >
                    {isSubmitting ? (
                      <>
                        <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                        Submitting...
                      </>
                    ) : (
                      <>
                        <Flag className="w-4 h-4" />
                        Submit Flag
                      </>
                    )}
                  </button>

                  {/* Attempts Info */}
                  {attemptsRemaining !== null && (
                    <p className="text-xs text-center text-muted-foreground">
                      {attemptsRemaining} attempts remaining
                    </p>
                  )}
                </form>
              )}
            </motion.div>

            {/* Challenge Stats */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="bg-white/5 border border-white/10 rounded-xl p-6"
            >
              <h3 className="text-sm font-medium text-muted-foreground mb-4">
                Challenge Stats
              </h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Users className="w-4 h-4" />
                    Solves
                  </div>
                  <span className="font-medium">-</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Clock className="w-4 h-4" />
                    First Blood
                  </div>
                  <span className="font-medium">-</span>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </main>

      {/* Terminal Drawer */}
      <TerminalDrawer
        isOpen={isTerminalOpen}
        onClose={() => setIsTerminalOpen(false)}
        containerId={challenge.connection_info?.container_id}
        challengeId={challenge.id}
        challengeTitle={challenge.title}
      />
    </div>
  );
}
