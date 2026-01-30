"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal, X, Maximize2, Minimize2, Power } from "lucide-react";
import { cn } from "@/lib/utils";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type TerminalType = any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type FitAddonType = any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type WebLinksAddonType = any;

// Dynamically import xterm to avoid SSR issues
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let XTermClass: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let FitAddonClass: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let WebLinksAddonClass: any = null;

interface TerminalDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  containerId?: string;
  challengeId?: string;
  challengeTitle?: string;
  className?: string;
}

export function TerminalDrawer({
  isOpen,
  onClose,
  containerId,
  challengeId,
  challengeTitle,
  className,
}: TerminalDrawerProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminalInstanceRef = useRef<TerminalType | null>(null);
  const fitAddonRef = useRef<FitAddonType | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modulesLoaded, setModulesLoaded] = useState(false);

  // Load xterm modules dynamically
  useEffect(() => {
    let mounted = true;

    const loadModules = async () => {
      try {
        const [{ Terminal }, { FitAddon }, { WebLinksAddon }] = await Promise.all([
          import("xterm"),
          import("xterm-addon-fit"),
          import("xterm-addon-web-links"),
        ]);

        if (mounted) {
          XTermClass = Terminal;
          FitAddonClass = FitAddon;
          WebLinksAddonClass = WebLinksAddon;
          setModulesLoaded(true);
        }
      } catch (err) {
        console.error("Failed to load xterm modules:", err);
        if (mounted) {
          setError("Failed to load terminal modules");
        }
      }
    };

    loadModules();

    return () => {
      mounted = false;
    };
  }, []);

  // Initialize terminal
  useEffect(() => {
    if (!isOpen || !modulesLoaded || !terminalRef.current || terminalInstanceRef.current) {
      return;
    }

    // Create terminal instance
    const term = new XTermClass({
      theme: {
        background: "#0a0a0f",
        foreground: "#e2e8f0",
        cursor: "#3b82f6",
        cursorAccent: "#0a0a0f",
        selectionBackground: "#3b82f6",
        selectionForeground: "#ffffff",
        black: "#1e1e2e",
        red: "#f38ba8",
        green: "#a6e3a1",
        yellow: "#f9e2af",
        blue: "#89b4fa",
        magenta: "#cba6f7",
        cyan: "#74c7ec",
        white: "#cdd6f4",
        brightBlack: "#45475a",
        brightRed: "#f38ba8",
        brightGreen: "#a6e3a1",
        brightYellow: "#f9e2af",
        brightBlue: "#89b4fa",
        brightMagenta: "#cba6f7",
        brightCyan: "#74c7ec",
        brightWhite: "#cdd6f4",
      },
      fontFamily: '"JetBrains Mono", "Fira Code", "Cascadia Code", monospace',
      fontSize: 14,
      lineHeight: 1.2,
      cursorBlink: true,
      cursorStyle: "block",
      scrollback: 10000,
      allowProposedApi: true,
    });

    // Create and load addons
    const fitAddon = new FitAddonClass();
    const webLinksAddon = new WebLinksAddonClass();

    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);

    // Open terminal in container
    term.open(terminalRef.current);

    // Initial fit
    setTimeout(() => {
      fitAddon.fit();
    }, 100);

    // Store refs
    terminalInstanceRef.current = term;
    fitAddonRef.current = fitAddon;

    // Welcome message
    term.writeln("\x1b[36m╔══════════════════════════════════════════════════════════════╗\x1b[0m");
    term.writeln("\x1b[36m║\x1b[0m           \x1b[1;34mCerberus CTF Platform - Terminal\x1b[0m                  \x1b[36m║\x1b[0m");
    term.writeln("\x1b[36m╚══════════════════════════════════════════════════════════════╝\x1b[0m");
    term.writeln("");

    if (challengeTitle) {
      term.writeln(`\x1b[33mChallenge:\x1b[0m ${challengeTitle}`);
    }

    term.writeln("\x1b[90mConnecting to container...\x1b[0m");
    term.writeln("");

    // Handle resize
    const handleResize = () => {
      fitAddon.fit();
      // Notify server of resize if connected
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        const { cols, rows } = term;
        wsRef.current.send(
          JSON.stringify({
            type: "resize",
            cols,
            rows,
          })
        );
      }
    };

    window.addEventListener("resize", handleResize);

    // Cleanup
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [isOpen, modulesLoaded, challengeTitle]);

  // Connect to WebSocket
  const connectWebSocket = useCallback(() => {
    if (!terminalInstanceRef.current || !containerId) {
      terminalInstanceRef.current?.writeln("\x1b[31mError: No container ID provided\x1b[0m");
      return;
    }

    setIsLoading(true);
    setError(null);

    // Get token from localStorage or cookie
    const token = localStorage.getItem("token") || "";

    // Build WebSocket URL
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProtocol}//${window.location.host}/api/ws/terminal/${containerId}?token=${encodeURIComponent(token)}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setIsLoading(false);
      terminalInstanceRef.current?.writeln("\x1b[32m✓ Connected to container\x1b[0m");
      terminalInstanceRef.current?.writeln("");

      // Send initial resize
      const dims = terminalInstanceRef.current;
      ws.send(
        JSON.stringify({
          type: "resize",
          cols: dims.cols,
          rows: dims.rows,
        })
      );
    };

    ws.onmessage = (event) => {
      if (event.data instanceof Blob) {
        // Binary data from container
        const reader = new FileReader();
        reader.onload = () => {
          const data = new Uint8Array(reader.result as ArrayBuffer);
          terminalInstanceRef.current?.write(data);
        };
        reader.readAsArrayBuffer(event.data);
      } else {
        // JSON control messages
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "error") {
            terminalInstanceRef.current?.writeln(`\x1b[31mError: ${msg.message}\x1b[0m`);
          }
        } catch {
          // Plain text message
          terminalInstanceRef.current?.write(event.data);
        }
      }
    };

    ws.onerror = () => {
      setIsLoading(false);
      setError("Connection error");
      terminalInstanceRef.current?.writeln("\x1b[31m✗ Connection error\x1b[0m");
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsLoading(false);
      terminalInstanceRef.current?.writeln("");
      terminalInstanceRef.current?.writeln("\x1b[33mConnection closed\x1b[0m");
    };

    // Handle terminal input
    terminalInstanceRef.current.onData((data: string) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    });
  }, [containerId]);

  // Connect when terminal is ready and containerId is provided
  useEffect(() => {
    if (isOpen && modulesLoaded && terminalInstanceRef.current && containerId && !wsRef.current) {
      connectWebSocket();
    }
  }, [isOpen, modulesLoaded, containerId, connectWebSocket]);

  // Cleanup on unmount or close
  useEffect(() => {
    if (!isOpen) {
      // Close WebSocket
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      // Dispose terminal
      if (terminalInstanceRef.current) {
        terminalInstanceRef.current.dispose();
        terminalInstanceRef.current = null;
      }

      fitAddonRef.current = null;
      setIsConnected(false);
      setIsLoading(false);
      setError(null);
    }
  }, [isOpen]);

  // Re-fit when expanded state changes
  useEffect(() => {
    if (isOpen && fitAddonRef.current) {
      setTimeout(() => {
        fitAddonRef.current?.fit();
      }, 300); // Wait for animation
    }
  }, [isExpanded, isOpen]);

  const handleReconnect = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    connectWebSocket();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ y: "100%" }}
          animate={{ y: 0 }}
          exit={{ y: "100%" }}
          transition={{ type: "spring", damping: 25, stiffness: 200 }}
          className={cn(
            "fixed left-0 right-0 z-50 bg-[#0a0a0f] border-t border-white/10 shadow-2xl",
            isExpanded ? "top-0 h-screen" : "bottom-0 h-[400px]",
            className
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-2 bg-white/5 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium text-foreground">
                  Terminal
                  {challengeTitle && (
                    <span className="text-muted-foreground ml-2">- {challengeTitle}</span>
                  )}
                </span>
              </div>

              {/* Connection Status */}
              <div className="flex items-center gap-2 ml-4">
                <div
                  className={cn(
                    "w-2 h-2 rounded-full",
                    isConnected ? "bg-emerald-500" : isLoading ? "bg-amber-500 animate-pulse" : "bg-rose-500"
                  )}
                />
                <span className="text-xs text-muted-foreground">
                  {isConnected ? "Connected" : isLoading ? "Connecting..." : "Disconnected"}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Reconnect Button */}
              {!isConnected && !isLoading && (
                <button
                  onClick={handleReconnect}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-foreground bg-white/5 hover:bg-white/10 rounded-md transition-colors"
                >
                  <Power className="w-3 h-3" />
                  Reconnect
                </button>
              )}

              {/* Expand/Collapse Button */}
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-white/5 rounded-md transition-colors"
                aria-label={isExpanded ? "Minimize" : "Maximize"}
              >
                {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>

              {/* Close Button */}
              <button
                onClick={onClose}
                className="p-1.5 text-muted-foreground hover:text-rose-400 hover:bg-rose-500/10 rounded-md transition-colors"
                aria-label="Close Terminal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Terminal Container */}
          <div className="relative flex-1 h-[calc(100%-48px)] p-2">
            {!modulesLoaded ? (
              <div className="flex items-center justify-center h-full">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                  <span className="text-sm">Loading terminal...</span>
                </div>
              </div>
            ) : (
              <div
                ref={terminalRef}
                className="h-full w-full rounded-md overflow-hidden bg-[#0a0a0f]"
              />
            )}

            {/* Error Overlay */}
            {error && (
              <div className="absolute inset-0 flex items-center justify-center bg-[#0a0a0f]/90">
                <div className="text-center">
                  <p className="text-rose-400 mb-4">{error}</p>
                  <button
                    onClick={handleReconnect}
                    className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                  >
                    Retry Connection
                  </button>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
