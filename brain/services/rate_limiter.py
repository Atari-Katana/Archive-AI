import time
from collections import defaultdict

# Simple in-memory rate limiter
class RateLimiter:
    """Simple in-memory rate limiter for public endpoints"""

    def __init__(self):
        # Track: {ip_address: [(timestamp1, timestamp2, ...)]}
        self.requests = defaultdict(list)
        self.window_seconds = 60  # 1 minute window
        self.max_requests = 30  # 30 requests per minute

    def is_allowed(self, client_ip: str) -> bool:
        """Check if request from client_ip is allowed"""
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean old requests outside the window
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > cutoff
        ]

        # Check if under limit
        if len(self.requests[client_ip]) < self.max_requests:
            self.requests[client_ip].append(now)
            return True

        return False

rate_limiter = RateLimiter()
