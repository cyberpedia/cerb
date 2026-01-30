"""
Security Middleware for Cerberus CTF Platform.

Implements WAF, rate limiting, honeypot, and security headers.
"""

import json
import re
import time
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# ============== Rate Limiting ==============

# Initialize slowapi limiter with default key function
limiter = Limiter(key_func=get_remote_address)


# ============== WAF Middleware ==============

# Blocked User-Agents (case-insensitive)
BLOCKED_USER_AGENTS = [
    "sqlmap",
    "nikto",
    "curl",
]

# Dangerous patterns to detect in request bodies
DANGEROUS_PATTERNS = [
    r"<script[^>]*>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe",
    r"<object",
    r"<embed",
    r"eval\s*\(",
    r"expression\s*\(",
]

# Compile patterns for efficiency
DANGEROUS_PATTERNS_COMPILED = [re.compile(pattern, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS]


class WAFMiddleware(BaseHTTPMiddleware):
    """
    Web Application Firewall Middleware.
    
    Blocks malicious requests based on:
    - User-Agent analysis
    - Dangerous content in request bodies
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through WAF rules."""
        # Check User-Agent
        user_agent = request.headers.get("user-agent", "").lower()
        for blocked_agent in BLOCKED_USER_AGENTS:
            if blocked_agent.lower() in user_agent:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access denied"},
                )

        # Check request body for dangerous content (JSON only)
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    body = await request.body()
                    if body:
                        body_str = body.decode("utf-8", errors="ignore")
                        for pattern in DANGEROUS_PATTERNS_COMPILED:
                            if pattern.search(body_str):
                                return JSONResponse(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    content={"detail": "Invalid request content"},
                                )
                        # Re-add body to request for downstream processing
                        await request.receive()
                except Exception:
                    # If body parsing fails, continue with request
                    pass

        return await call_next(request)


# ============== Honeypot ==============

# Simple in-memory ban store (in production, use Redis or database)
# Format: {ip_address: banned_until_timestamp}
_banned_ips: dict[str, float] = {}

# Honeypot access tracking (count accesses before ban)
_honeypot_accesses: dict[str, int] = {}

# Ban duration in seconds (24 hours)
BAN_DURATION = 24 * 60 * 60

# Number of honeypot accesses before ban
HONEYPOT_BAN_THRESHOLD = 1


class HoneypotMiddleware(BaseHTTPMiddleware):
    """
    Honeypot Middleware.
    
    Tracks and auto-bans IPs that access honeypot endpoints.
    Also checks if incoming requests are from banned IPs.
    """

    def _is_banned(self, ip_address: str) -> bool:
        """Check if IP is currently banned."""
        if ip_address in _banned_ips:
            if time.time() < _banned_ips[ip_address]:
                return True
            else:
                # Ban expired, remove from store
                del _banned_ips[ip_address]
                _honeypot_accesses.pop(ip_address, None)
        return False

    def _ban_ip(self, ip_address: str) -> None:
        """Ban an IP address."""
        _banned_ips[ip_address] = time.time() + BAN_DURATION
        _honeypot_accesses.pop(ip_address, None)

    def _record_honeypot_access(self, ip_address: str) -> bool:
        """
        Record honeypot access for an IP.
        Returns True if IP should be banned.
        """
        _honeypot_accesses[ip_address] = _honeypot_accesses.get(ip_address, 0) + 1
        return _honeypot_accesses[ip_address] >= HONEYPOT_BAN_THRESHOLD

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check for banned IPs and honeypot access."""
        ip_address = get_remote_address(request)

        # Check if IP is banned
        if self._is_banned(ip_address):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access denied"},
            )

        # Check if accessing honeypot endpoint
        if request.url.path == "/admin/debug":
            should_ban = self._record_honeypot_access(ip_address)
            if should_ban:
                self._ban_ip(ip_address)
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Not found"},
            )

        return await call_next(request)


def get_banned_ips() -> dict[str, float]:
    """Get currently banned IPs (for admin/monitoring purposes)."""
    current_time = time.time()
    # Clean expired bans
    expired = [ip for ip, until in _banned_ips.items() if current_time > until]
    for ip in expired:
        del _banned_ips[ip]
    return _banned_ips.copy()


def unban_ip(ip_address: str) -> bool:
    """Manually unban an IP address."""
    if ip_address in _banned_ips:
        del _banned_ips[ip_address]
        _honeypot_accesses.pop(ip_address, None)
        return True
    return False


# ============== Security Headers ==============

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security Headers Middleware.
    
    Adds security headers to all responses:
    - HSTS (HTTP Strict Transport Security)
    - CSP (Content Security Policy)
    - X-Frame-Options
    - X-Content-Type-Options
    - X-XSS-Protection
    - Referrer-Policy
    """

    def __init__(
        self,
        app: FastAPI,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = True,
    ):
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # HSTS - HTTP Strict Transport Security
        hsts_value = f"max-age={self.hsts_max_age}"
        if self.hsts_include_subdomains:
            hsts_value += "; includeSubDomains"
        if self.hsts_preload:
            hsts_value += "; preload"
        response.headers["Strict-Transport-Security"] = hsts_value

        # CSP - Content Security Policy
        csp_value = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers["Content-Security-Policy"] = csp_value

        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        return response


# ============== Rate Limit Exception Handler ==============

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded errors."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "retry_after": exc.description if hasattr(exc, "description") else None,
        },
        headers={"Retry-After": str(exc.description) if hasattr(exc, "description") else "60"},
    )


# ============== Setup Function ==============

def setup_security_middleware(app: FastAPI) -> None:
    """
    Setup all security middleware for the FastAPI application.
    
    This function should be called after creating the FastAPI app
    but before adding routes.
    """
    # Add rate limiter to app state
    app.state.limiter = limiter

    # Add rate limit exception handler
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Add middleware (order matters - first added is outermost)
    # Honeypot first to catch banned IPs early
    app.add_middleware(HoneypotMiddleware)
    
    # WAF next to filter malicious requests
    app.add_middleware(WAFMiddleware)
    
    # Security headers last to ensure all responses get headers
    app.add_middleware(SecurityHeadersMiddleware)


# ============== Decorators for Rate Limiting ==============

def rate_limit_submit() -> Callable:
    """Rate limit decorator for flag submission endpoint (10/min)."""
    return limiter.limit("10/minute")


def rate_limit_login() -> Callable:
    """Rate limit decorator for login endpoint (5/min)."""
    return limiter.limit("5/minute")
