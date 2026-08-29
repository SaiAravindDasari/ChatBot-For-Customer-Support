"""
Enterprise Security Hardening Middleware & Utilities for QueryDesk.
Includes HTTP Security Headers (CSP, HSTS, X-Frame-Options), Input Sanitization,
and Cross-Site Scripting (XSS) Prevention.
"""

import html
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies enterprise-grade security headers to all HTTP responses.
    Protects against Clickjacking, MIME-sniffing, XSS, and unauthorized framing.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Frame protection (allow framing only within same origin if needed)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        
        # Legacy XSS protection for older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(self), camera=()"
        
        # Content Security Policy (allows CDNs for fonts and Chart.js, permits WebSockets)
        csp_directives = [
            "default-src 'self' http: https: ws: wss:",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com data:",
            "img-src 'self' data: https: blob:",
            "connect-src 'self' ws: wss: http: https:",
            "frame-ancestors 'self'"
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        return response


def sanitize_input(text: str, max_length: int = 4000) -> str:
    """
    Sanitize untrusted user input:
    1. Truncate to maximum safe length.
    2. Strip dangerous control characters.
    3. Escape HTML tags to prevent XSS.
    """
    if not isinstance(text, str):
        return ""
    
    # Truncate
    cleaned = text[:max_length]
    
    # Strip null bytes and non-printable control chars (except standard newlines/tabs)
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned)
    
    # HTML escape
    cleaned = html.escape(cleaned.strip())
    
    return cleaned
