"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Github, Chrome, Eye, EyeOff, Terminal, Lock, User } from "lucide-react";

interface LoginFormProps {
  onSuccess?: () => void;
  enableGitHub?: boolean;
  enableGoogle?: boolean;
}

interface TerminalInputProps {
  label: string;
  type?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  icon?: React.ReactNode;
  onKeyDown?: (e: React.KeyboardEvent) => void;
}

const TerminalInput: React.FC<TerminalInputProps> = ({
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  icon,
  onKeyDown,
}) => {
  const [isFocused, setIsFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const displayType = type === "password" && showPassword ? "text" : type;

  return (
    <div className="mb-6">
      <label className="block text-green-500 text-xs mb-2 font-mono tracking-wider opacity-70">
        {`> ${label}`}
      </label>
      <div
        className={`relative flex items-center border-b-2 transition-all duration-300 ${
          isFocused
            ? "border-green-400 shadow-[0_2px_10px_rgba(74,222,128,0.3)]"
            : "border-green-900/50"
        }`}
        onClick={() => inputRef.current?.focus()}
      >
        {icon && (
          <span className="text-green-600 mr-3 flex-shrink-0">{icon}</span>
        )}
        <span className="text-green-500 font-mono mr-2">$</span>
        <input
          ref={inputRef}
          type={displayType}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyDown={onKeyDown}
          className="flex-1 bg-transparent text-green-400 font-mono text-sm py-3 outline-none placeholder-green-800/50"
          placeholder={placeholder}
          spellCheck={false}
          autoComplete="off"
        />
        {type === "password" && value && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setShowPassword(!showPassword);
            }}
            className="text-green-600 hover:text-green-400 transition-colors ml-2"
          >
            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        )}
        <motion.span
          animate={{ opacity: isFocused ? 1 : 0 }}
          className="ml-2 w-2 h-5 bg-green-400"
          transition={{ duration: 0.1 }}
        />
      </div>
    </div>
  );
};

const TypingEffect: React.FC<{ text: string; onComplete?: () => void }> = ({
  text,
  onComplete,
}) => {
  const [displayText, setDisplayText] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setDisplayText((prev) => prev + text[currentIndex]);
        setCurrentIndex((prev) => prev + 1);
      }, 50);
      return () => clearTimeout(timeout);
    } else {
      onComplete?.();
    }
  }, [currentIndex, text, onComplete]);

  return (
    <span className="font-mono">
      {displayText}
      {currentIndex < text.length && (
        <motion.span
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.5, repeat: Infinity }}
          className="inline-block w-2 h-5 bg-green-400 ml-1 align-middle"
        />
      )}
    </span>
  );
};

export const LoginForm: React.FC<LoginFormProps> = ({
  onSuccess,
  enableGitHub = true,
  enableGoogle = true,
}) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setError(null);
    setIsLoading(true);

    // Simulate authentication delay
    await new Promise((resolve) => setTimeout(resolve, 1500));

    // Mock validation
    if (username.length < 3 || password.length < 6) {
      setError("AUTHENTICATION_FAILED: Invalid credentials");
      setIsLoading(false);
      return;
    }

    setIsLoading(false);
    setShowSuccess(true);
  };

  const handleOAuth = (provider: string) => {
    console.log(`OAuth login with ${provider}`);
    // Implement OAuth flow
  };

  if (showSuccess) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex flex-col items-center justify-center h-full p-8"
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 15 }}
          className="w-20 h-20 rounded-full border-4 border-green-500 flex items-center justify-center mb-6"
        >
          <motion.svg
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            className="w-10 h-10 text-green-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <motion.path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={3}
              d="M5 13l4 4L19 7"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            />
          </motion.svg>
        </motion.div>
        <div className="text-green-400 font-mono text-xl text-center">
          <TypingEffect
            text="ACCESS GRANTED"
            onComplete={() => {
              setTimeout(onSuccess, 1000);
            }}
          />
        </div>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="mt-4 text-green-600 font-mono text-xs"
        >
          Redirecting to secure environment...
        </motion.div>
      </motion.div>
    );
  }

  return (
    <div className="w-full max-w-md">
      {/* Terminal Header */}
      <div className="flex items-center gap-2 mb-8">
        <Terminal className="w-6 h-6 text-green-500" />
        <span className="text-green-400 font-mono text-lg tracking-wider">
          SECURE_LOGIN.exe
        </span>
      </div>

      {/* Error Message */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-6 p-3 bg-red-950/50 border border-red-800 rounded"
          >
            <span className="text-red-400 font-mono text-xs">{error}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Login Form */}
      <form onSubmit={handleSubmit}>
        <TerminalInput
          label="ENTER_USERNAME"
          value={username}
          onChange={setUsername}
          placeholder="username"
          icon={<User size={16} />}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        />

        <TerminalInput
          label="ENTER_PASSWORD"
          type="password"
          value={password}
          onChange={setPassword}
          placeholder="••••••••"
          icon={<Lock size={16} />}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        />

        {/* Submit Button */}
        <motion.button
          type="submit"
          disabled={isLoading || !username || !password}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className={`w-full mt-6 py-4 font-mono text-sm tracking-widest border-2 transition-all duration-300 ${
            isLoading || !username || !password
              ? "border-green-900/30 text-green-900/30 cursor-not-allowed"
              : "border-green-500 text-green-400 hover:bg-green-500/10 hover:shadow-[0_0_20px_rgba(74,222,128,0.3)]"
          }`}
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <motion.span
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="inline-block w-4 h-4 border-2 border-green-500 border-t-transparent rounded-full"
              />
              AUTHENTICATING...
            </span>
          ) : (
            "[ EXECUTE_LOGIN ]"
          )}
        </motion.button>
      </form>

      {/* OAuth Section */}
      {(enableGitHub || enableGoogle) && (
        <div className="mt-8">
          <div className="flex items-center gap-4 mb-6">
            <div className="flex-1 h-px bg-green-900/50" />
            <span className="text-green-700 font-mono text-xs">
              ALTERNATE_ACCESS
            </span>
            <div className="flex-1 h-px bg-green-900/50" />
          </div>

          <div className="flex gap-4">
            {enableGitHub && (
              <motion.button
                type="button"
                onClick={() => handleOAuth("github")}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="flex-1 py-3 border border-green-800/50 text-green-400 font-mono text-xs hover:border-green-500 hover:bg-green-500/10 transition-all duration-300 flex items-center justify-center gap-2"
              >
                <Github size={16} />
                GITHUB
              </motion.button>
            )}
            {enableGoogle && (
              <motion.button
                type="button"
                onClick={() => handleOAuth("google")}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="flex-1 py-3 border border-green-800/50 text-green-400 font-mono text-xs hover:border-green-500 hover:bg-green-500/10 transition-all duration-300 flex items-center justify-center gap-2"
              >
                <Chrome size={16} />
                GOOGLE
              </motion.button>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-8 text-center">
        <p className="text-green-700 font-mono text-xs">
          {`> SYSTEM_VERSION: v2.4.1 | PROTOCOL: SECURE`}
        </p>
      </div>
    </div>
  );
};

export default LoginForm;
