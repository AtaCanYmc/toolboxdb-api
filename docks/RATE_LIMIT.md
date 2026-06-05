# Rate Limiting Middleware Implementation Guide

## Overview
This document explains the Redis-based Rate Limiting Middleware implementation for the ToolboxDB API.

## Features

✅ **Fixed Window Counter Algorithm**: Uses Redis atomic operations (`INCR`) for thread-safe counting
✅ **Granular Per-Endpoint Limits**: Different limits for different endpoints
✅ **HTTP 429 Response**: Proper "Too Many Requests" status code with headers
✅ **Standard Rate-Limit Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
✅ **Fail-Safe Design**: If Redis is unavailable, requests pass through (Fail-Open strategy)
✅ **IP-Based Identification**: Supports X-Forwarded-For for reverse proxy scenarios
✅ **Correlation ID Integration**: Works seamlessly with existing X-Correlation-ID middleware
✅ **Debug Logging**: Integrates with Python's standard logging

## Architecture

### Component Interaction

```
Incoming Request
    ↓
CORS Middleware
    ↓
Rate Limit Middleware ← Redis Client
    ↓
Correlation ID Middleware
    ↓
Route Handler
    ↓
Response (with rate-limit headers attached)
```

### Middleware Registration Order

The order of middleware registration is important:

1. **CORS Middleware** (outermost) - Handles browser preflight requests
2. **RateLimitMiddleware** - Checks rate limits before routing
3. **LoggingAndCorrelationMiddleware** - Adds correlation IDs to all requests

This order ensures:
- Rate limits are enforced early
- Denied requests (429) are logged with correlation IDs
- Correlation IDs are available in logs for all requests

## Configuration

### Default Rate Limits

The rate limits are defined in `src/middleware/rate_limit.py` in the `RATE_LIMIT_CONFIG` dictionary:

```python
RATE_LIMIT_CONFIG: Dict[str, Tuple[int, int]] = {
    "/api/v1/invoices/upload": (5, 60),       # 5 requests per 60 seconds
    "/api/v1/invoices": (20, 60),             # 20 requests per 60 seconds
    "/api/v1/components": (60, 60),           # 60 requests per 60 seconds
    "/api/v1/categories": (60, 60),           # 60 requests per 60 seconds
    "default": (60, 60),                      # Fallback: 60 per minute
}
```

### Customizing Limits

To add or modify rate limits:

1. **Edit `RATE_LIMIT_CONFIG` dictionary** in `src/middleware/rate_limit.py`:

```python
RATE_LIMIT_CONFIG: Dict[str, Tuple[int, int]] = {
    "/api/v1/invoices/upload": (5, 60),       # Heavy LLM endpoint: 5 req/min
    "/api/v1/invoices": (20, 60),             # Invoice queries: 20 req/min
    "/api/v1/components": (60, 60),           # Standard: 60 req/min
    "/api/v1/categories": (60, 60),           # Standard: 60 req/min
    "/api/v1/search": (30, 60),               # Search: 30 req/min (example)
    "default": (60, 60),                      # Global default
}
```

2. **Restart the application** for changes to take effect.

### Rate Limit Format

Each entry is a tuple: `(max_requests, window_size_seconds)`

- **max_requests**: Maximum number of requests allowed within the window
- **window_size_seconds**: Time window in seconds (typically 60 for per-minute limits)

**Examples:**
- `(5, 60)` = 5 requests per minute
- `(100, 3600)` = 100 requests per hour
- `(1, 60)` = 1 request per minute (maximum protection)

## How It Works

### Algorithm: Fixed Window Counter

1. **Client Identification**: Extract client IP from request
   - Priority: `X-Forwarded-For` header → Request client IP → "unknown"
   
2. **Key Construction**: Create unique Redis key per route/client/minute
   - Format: `rate_limit:{path}:{client_id}:{window_start}`
   - Example: `rate_limit:/api/v1/invoices/upload:192.168.1.100:1717594860`

3. **Atomic Increment**: Use Redis `INCR` command
   - If count > max_requests: limit exceeded
   - If count == 1: set expiry to window_size seconds
   
4. **Response**:
   - If exceeded: Return `429 Too Many Requests` with retry info
   - If allowed: Continue to handler, attach rate-limit headers

### Example Flow

```
Request from 192.168.1.100 at 11:01:00
Window period: every 60 seconds (fixed at 11:01:00 - 11:01:60)

Request 1: counter = 1 → allowed (remaining: 4)
Request 2: counter = 2 → allowed (remaining: 3)
Request 3: counter = 3 → allowed (remaining: 2)
Request 4: counter = 4 → allowed (remaining: 1)
Request 5: counter = 5 → allowed (remaining: 0)
Request 6: counter = 6 → DENIED (429, retry after 60s)
...
at 11:02:00: window resets, counter resets to 0
```

## HTTP Responses

### Success Response (200-399)

Request header: Any normal request within limits

Response headers:
```
X-RateLimit-Limit: 5              # Max requests per window
X-RateLimit-Remaining: 2          # Requests left in current window
X-RateLimit-Reset: 1717594920     # Unix timestamp when limit resets
```

### Rate Limit Exceeded (429)

Request header: 6th request within 60 seconds when limit is 5

Response status: `429 Too Many Requests`

Response body:
```json
{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded. Max 5 requests per 60 seconds.",
  "retry_after": 15
}
```

Response headers:
```
X-RateLimit-Limit: 5              # Max requests per window
X-RateLimit-Remaining: 0          # No requests left
X-RateLimit-Reset: 1717594920     # Unix timestamp when limit resets
Retry-After: 15                    # Seconds to wait before retrying
```

## Fail-Safe Behavior

If Redis is unavailable or a rate-limit check fails:

1. **Log the error** with correlation ID:
   ```
   ERROR Rate limit check failed for client 192.168.1.100: ConnectionError. Allowing request (fail-safe).
   ```

2. **Allow the request** to proceed (Fail-Open strategy)
   - The application continues to function
   - Users are not blocked by infrastructure issues
   - The problem is clearly logged for monitoring

3. **Monitor Redis health**
   - Use `/health` endpoint to check overall system health
   - Monitor logs for repeated rate-limit errors
   - Set up alerts on ERROR logs containing "Rate limit check failed"

## Client Identification

### IP Address Extraction

The middleware extracts client IP in this order of precedence:

1. **X-Forwarded-For** header (reverse proxy scenario)
   ```
   X-Forwarded-For: 203.0.113.45, 198.51.100.178
   # Uses: 203.0.113.45 (client's original IP)
   ```

2. **Request client IP** (direct connection)
   ```
   # Uses: socket connection source IP
   ```

3. **Fallback** to "unknown" (rare)
   ```
   # Uses: "unknown" identifier
   ```

### IPv6 Support

IPv6 addresses are supported:
```
# IPv6 client
2001:db8::1 → rate_limit:/api/v1/invoices/upload:2001:db8::1:window
```

## Integration Examples

### Example 1: Protected Invoice Upload

Request 1-5: Normal requests, counters show remaining capacity
```bash
curl -X POST http://localhost:8000/api/v1/invoices/upload \
  -F "file=@invoice.pdf" \
  -H "X-Correlation-ID: req-001"

# Response headers:
# X-RateLimit-Limit: 5
# X-RateLimit-Remaining: 4
# X-RateLimit-Reset: 1717594920
```

Request 6: Exceeds limit
```bash
curl -X POST http://localhost:8000/api/v1/invoices/upload \
  -F "file=@invoice.pdf" \
  -H "X-Correlation-ID: req-006"

# Status: 429 Too Many Requests
# Response:
# {
#   "error": "Too Many Requests",
#   "message": "Rate limit exceeded. Max 5 requests per 60 seconds.",
#   "retry_after": 45
# }
```

### Example 2: Standard Endpoint (Higher Limit)

```bash
# 60 requests per minute allowed
curl http://localhost:8000/api/v1/components \
  -H "X-Correlation-ID: req-list-components"

# Succeeds for first 60 requests
# Request 61 returns 429
```

## Logging & Monitoring

### Log Levels

**DEBUG**: Successful rate-limit checks (verbose, use for development)
```
DEBUG: Request allowed for client 192.168.1.100 on /api/v1/invoices/upload (used: 3/5)
```

**WARNING**: Rate limit exceeded (important, need to monitor)
```
WARNING: Rate limit exceeded for client 192.168.1.100 on /api/v1/invoices/upload (limit: 5/60s)
```

**ERROR**: Rate limit check infrastructure failure (critical, needs investigation)
```
ERROR: Rate limit check failed for client 192.168.1.100: ConnectionError. Allowing request (fail-safe).
```

### Enable Debug Logging

In your application configuration:
```python
import logging

# Configure rate limit logging to DEBUG level
logging.getLogger("src.middleware.rate_limit").setLevel(logging.DEBUG)
```

### Monitoring Checklist

- [ ] Monitor 429 response rates by endpoint
- [ ] Alert on repeated rate-limit infrastructure errors
- [ ] Track client IPs with high rejection rates (potential DoS attack)
- [ ] Monitor Redis memory usage for rate-limit keys
- [ ] Set up alerts for Redis unavailability

## Skills Applied

✅ **Async/Await Patterns**: Full async Python with Redis async client
✅ **Middleware Architecture**: FastAPI middleware stack and request/response lifecycle
✅ **Atomic Operations**: Redis `INCR` and `EXPIRE` for race-condition prevention
✅ **HTTP Standards**: RFC 6585 (429 status code), RFC 7231 (Retry-After header)
✅ **Error Handling**: Graceful degradation and fail-safe design
✅ **Observability**: Structured logging with correlation IDs
✅ **Type Safety**: Full type hints throughout
✅ **Docstring Standards**: Given-When-Then format for clarity

## Testing the Middleware

### Manual Testing (cURL)

```bash
# Test 1: Make 5 successful requests to /api/v1/invoices/upload
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/invoices/upload \
    -F "file=@test.pdf" \
    -H "X-Correlation-ID: test-$i" \
    -w "\nStatus: %{http_code}\n\n"
done

# Test 2: 6th request should be rate-limited
curl -X POST http://localhost:8000/api/v1/invoices/upload \
  -F "file=@test.pdf" \
  -H "X-Correlation-ID: test-6"
# Expected: 429 Too Many Requests
```

### Automated Testing (Pytest)

See `tests/test_rate_limit.py` (to be created) for comprehensive test coverage.

## Production Considerations

### 1. Redis Persistence

Ensure your Redis instance is properly configured:
- Enable AOF (Append Only File) or RDB snapshots
- Configure replication for high availability
- Set up monitoring and alerting

### 2. Memory Management

Rate-limit keys automatically expire after `window_size` seconds:
```
Memory per key: ~50 bytes (key + metadata)
Max keys per minute: routes × unique_ips
Example: 5 routes × 10,000 clients = 50,000 keys = ~2.5MB
```

### 3. Scaling Considerations

- **Single Redis instance**: Sufficient for most applications
- **Redis Cluster**: Use for very high traffic scenarios
- **Rate-limit distribution**: Current implementation is per-Redis-node

### 4. DDoS Mitigation

While useful, rate limiting is not sufficient for DDoS protection:
- Deploy WAF (Web Application Firewall) for L7 DDoS
- Use CDN with DDoS protection (Cloudflare, AWS Shield)
- Implement IP-level rate limiting at infrastructure level

## Future Enhancements

Potential improvements for future versions:

1. **Sliding Window Log**: More precise algorithm, higher memory usage
2. **User-based Limits**: Identify by user ID instead of just IP
3. **Dynamic Limits**: Adjust limits based on user tier or history
4. **Rate Limit Quotas**: Daily/monthly allowances in addition to per-minute
5. **Distributed Rate Limiting**: Synchronize limits across multiple instances
6. **Custom Rate-Limit Headers**: Include `X-RateLimit-*` in error responses

---

**Version**: 1.0.0
**Last Updated**: June 5, 2026
**Framework**: FastAPI + Uvicorn
**Database**: PostgreSQL (via Supabase)
**Cache**: Redis

