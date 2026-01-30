"use client";

import React, { useEffect, useRef, useState } from "react";
import { motion, useAnimationFrame } from "framer-motion";
import { LoginForm } from "@/components/auth/LoginForm";

// 3D Wireframe Cube Animation Component
const WireframeCube: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rotationRef = useRef({ x: 0, y: 0, z: 0 });

  useAnimationFrame(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Update rotation
    rotationRef.current.x += 0.005;
    rotationRef.current.y += 0.008;
    rotationRef.current.z += 0.003;

    // Clear canvas
    ctx.fillStyle = "rgba(0, 0, 0, 0.1)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Cube vertices
    const size = 120;
    const vertices = [
      { x: -size, y: -size, z: -size },
      { x: size, y: -size, z: -size },
      { x: size, y: size, z: -size },
      { x: -size, y: size, z: -size },
      { x: -size, y: -size, z: size },
      { x: size, y: -size, z: size },
      { x: size, y: size, z: size },
      { x: -size, y: size, z: size },
    ];

    // Edges connecting vertices
    const edges = [
      [0, 1], [1, 2], [2, 3], [3, 0], // Back face
      [4, 5], [5, 6], [6, 7], [7, 4], // Front face
      [0, 4], [1, 5], [2, 6], [3, 7], // Connecting edges
    ];

    // Rotation matrices
    const rotateX = (point: { x: number; y: number; z: number }, angle: number) => {
      const cos = Math.cos(angle);
      const sin = Math.sin(angle);
      return {
        x: point.x,
        y: point.y * cos - point.z * sin,
        z: point.y * sin + point.z * cos,
      };
    };

    const rotateY = (point: { x: number; y: number; z: number }, angle: number) => {
      const cos = Math.cos(angle);
      const sin = Math.sin(angle);
      return {
        x: point.x * cos + point.z * sin,
        y: point.y,
        z: -point.x * sin + point.z * cos,
      };
    };

    const rotateZ = (point: { x: number; y: number; z: number }, angle: number) => {
      const cos = Math.cos(angle);
      const sin = Math.sin(angle);
      return {
        x: point.x * cos - point.y * sin,
        y: point.x * sin + point.y * cos,
        z: point.z,
      };
    };

    // Project 3D point to 2D
    const project = (point: { x: number; y: number; z: number }) => {
      const distance = 400;
      const scale = distance / (distance + point.z);
      return {
        x: canvas.width / 2 + point.x * scale,
        y: canvas.height / 2 + point.y * scale,
      };
    };

    // Transform vertices
    const transformedVertices = vertices.map((v) => {
      let point = rotateX(v, rotationRef.current.x);
      point = rotateY(point, rotationRef.current.y);
      point = rotateZ(point, rotationRef.current.z);
      return project(point);
    });

    // Draw edges
    ctx.strokeStyle = "#4ade80";
    ctx.lineWidth = 2;
    ctx.shadowBlur = 10;
    ctx.shadowColor = "#4ade80";

    edges.forEach(([start, end]) => {
      ctx.beginPath();
      ctx.moveTo(transformedVertices[start].x, transformedVertices[start].y);
      ctx.lineTo(transformedVertices[end].x, transformedVertices[end].y);
      ctx.stroke();
    });

    // Draw vertices
    ctx.fillStyle = "#4ade80";
    transformedVertices.forEach((v) => {
      ctx.beginPath();
      ctx.arc(v.x, v.y, 4, 0, Math.PI * 2);
      ctx.fill();
    });

    // Draw center glow
    const gradient = ctx.createRadialGradient(
      canvas.width / 2,
      canvas.height / 2,
      0,
      canvas.width / 2,
      canvas.height / 2,
      200
    );
    gradient.addColorStop(0, "rgba(74, 222, 128, 0.1)");
    gradient.addColorStop(1, "rgba(74, 222, 128, 0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  });

  return (
    <canvas
      ref={canvasRef}
      width={600}
      height={600}
      className="w-full h-full"
    />
  );
};

// Matrix Rain Effect Component
const MatrixRain: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;

    const chars = "01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン";
    const fontSize = 14;
    const columns = Math.floor(canvas.width / fontSize);
    const drops: number[] = new Array(columns).fill(1);

    let animationId: number;

    const draw = () => {
      ctx.fillStyle = "rgba(0, 0, 0, 0.05)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.fillStyle = "#0f0";
      ctx.font = `${fontSize}px monospace`;

      for (let i = 0; i < drops.length; i++) {
        const text = chars[Math.floor(Math.random() * chars.length)];
        ctx.fillText(text, i * fontSize, drops[i] * fontSize);

        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
          drops[i] = 0;
        }
        drops[i]++;
      }

      animationId = requestAnimationFrame(draw);
    };

    draw();

    const handleResize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };

    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 opacity-20 pointer-events-none"
    />
  );
};

// Scan Line Effect
const ScanLines: React.FC = () => (
  <div className="absolute inset-0 pointer-events-none overflow-hidden">
    <div
      className="absolute inset-0"
      style={{
        background:
          "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 255, 0, 0.03) 2px, rgba(0, 255, 0, 0.03) 4px)",
      }}
    />
  </div>
);

export default function LoginPage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleLoginSuccess = () => {
    // Redirect to dashboard or home
    window.location.href = "/dashboard";
  };

  if (!mounted) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-green-500 font-mono animate-pulse">
          INITIALIZING_SYSTEM...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black flex overflow-hidden">
      {/* Left Side - Form */}
      <motion.div
        initial={{ opacity: 0, x: -50 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="w-full lg:w-1/2 flex items-center justify-center p-8 relative"
      >
        {/* Background Grid */}
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `
              linear-gradient(rgba(74, 222, 128, 0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(74, 222, 128, 0.1) 1px, transparent 1px)
            `,
            backgroundSize: "50px 50px",
          }}
        />

        {/* Scan Lines */}
        <ScanLines />

        {/* Form Container */}
        <div className="relative z-10 w-full max-w-md">
          <LoginForm
            onSuccess={handleLoginSuccess}
            enableGitHub={true}
            enableGoogle={true}
          />
        </div>
      </motion.div>

      {/* Right Side - 3D Animation */}
      <motion.div
        initial={{ opacity: 0, x: 50 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: "easeOut", delay: 0.2 }}
        className="hidden lg:flex w-1/2 relative items-center justify-center bg-gradient-to-br from-black via-green-950/20 to-black"
      >
        {/* Matrix Rain Background */}
        <MatrixRain />

        {/* Grid Background */}
        <div
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: `
              linear-gradient(rgba(74, 222, 128, 0.3) 1px, transparent 1px),
              linear-gradient(90deg, rgba(74, 222, 128, 0.3) 1px, transparent 1px)
            `,
            backgroundSize: "40px 40px",
            perspective: "1000px",
            transform: "rotateX(60deg)",
            transformOrigin: "center top",
          }}
        />

        {/* 3D Wireframe Cube */}
        <div className="relative z-10">
          <WireframeCube />
        </div>

        {/* Decorative Elements */}
        <div className="absolute bottom-8 left-8 right-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1, duration: 0.5 }}
            className="flex items-center gap-4"
          >
            <div className="flex-1 h-px bg-gradient-to-r from-transparent via-green-500 to-transparent" />
            <span className="text-green-500/50 font-mono text-xs tracking-widest">
              SECURE_CONNECTION_ESTABLISHED
            </span>
            <div className="flex-1 h-px bg-gradient-to-r from-transparent via-green-500 to-transparent" />
          </motion.div>
        </div>

        {/* Corner Decorations */}
        <div className="absolute top-8 left-8 w-16 h-16 border-l-2 border-t-2 border-green-500/30" />
        <div className="absolute top-8 right-8 w-16 h-16 border-r-2 border-t-2 border-green-500/30" />
        <div className="absolute bottom-8 left-8 w-16 h-16 border-l-2 border-b-2 border-green-500/30" />
        <div className="absolute bottom-8 right-8 w-16 h-16 border-r-2 border-b-2 border-green-500/30" />

        {/* Status Indicators */}
        <div className="absolute top-8 left-1/2 -translate-x-1/2 flex items-center gap-2">
          <motion.div
            animate={{ opacity: [1, 0.5, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="w-2 h-2 rounded-full bg-green-500"
          />
          <span className="text-green-500/70 font-mono text-xs">
            SERVER_ONLINE
          </span>
        </div>
      </motion.div>
    </div>
  );
}
