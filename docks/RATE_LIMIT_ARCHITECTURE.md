# Rate Limiting Architecture & Best Practices

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client (Browser/App)                         │
│                                                                     │
│  curl http://localhost:8000/api/v1/invoices/upload                 │
│  Headers: X-Correlation-ID: req-001                                │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ 1. CORS Middleware                                          │  │
│  │    - Handles preflight requests (OPTIONS)                   │  │
│  │    - Allows cross-origin requests                           │  │
│  └────────────────┬────────────────────────────────────────────┘  │
│                   │                                                │
│  ┌────────────────▼────────────────────────────────────────────┐  │
│  │ 2. RateLimitMiddleware  ◄──────────────────┐               │  │
│  │    - Extract client IP                     │               │  │
│  │    - Determine rate limit for route        │               │  │
│  │    - Check Redis atomic counter            │               │  │
│  │    - Return 429 if exceeded                │               │  │
│  │    - Attach rate-limit headers             │               │  │
│  └────────────────┬─────────────────────────────────────────┐ │  │
│                   │                           │               │ │  │
│                   │                  ┌────────▼─────────┐     │ │  │
│                   │                  │  Redis Client    │     │ │  │
│                   │                  │  (via async)     │     │ │  │
│                   │                  │                  │     │ │  │
│                   │                  │ Keys:            │     │ │  │
│                   │                  │ rate_limit:...   │     │ │  │
│                   │                  │ TTL: 60s         │     │ │  │
│                   │                  └──────────────────┘     │ │  │
│  ┌────────────────▼─────────────────────────────────────────┐ │  │
│  │ 3. LoggingAndCorrelationMiddleware                       │ │  │
│  │    - Assign/preserve X-Correlation-ID                    │ │  │
│  │    - Log request start/end with correlation ID          │ │  │
│  │    - Attach correlation ID to response                  │ │  │
│  └────────────────┬──────────────────────────────────────────┘ │  │
│                   │                                                │
│  ┌────────────────▼──────────────────────────────────────────┐  │
│  │ 4. Route Handler                                           │  │
│  │    - /api/v1/invoices/upload                              │  │
│  │    - /api/v1/invoices                                     │  │
│  │    - /api/v1/components                                   │  │
│  │    - etc.                                                 │  │
│  └────────────────┬──────────────────────────────────────────┘  │
│                   │                                                │
│  ┌────────────────▼──────────────────────────────────────────┐  │
│  │ 5. Response Assembly                                       │  │
│  │    - Add X-RateLimit-Limit header                          │  │
│  │    - Add X-RateLimit-Remaining header                      │  │
│  │    - Add X-RateLimit-Reset header                          │  │
│  │    - Return to client                                      │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Client Response                                  │
│                                                                     │
│  HTTP/1.1 200 OK                                                    │
│  X-RateLimit-Limit: 5                                               │
│  X-RateLimit-Remaining: 2                                           │
│  X-RateLimit-Reset: 1717594920                                      │
│  X-Correlation-ID: req-001                                          │
│                                                                     │
│  {"message": "Invoice uploaded and parsed successfully"}            │
└─────────────────────────────────────────────────────────────────────┘
```

## Request Flow: Rate Limit Check

```
Incoming Request
    │
    ├─► Extract Client IP
    │   - X-Forwarded-For? → use first IP
    │   - request.client? → use client.host
    │   - else → use "unknown"
    │
    ├─► Determine Rate Limit
    │   - Route: /api/v1/invoices/upload? → (5, 60)
    │   - Route: /api/v1/invoices? → (20, 60)
    │   - Route: default → (60, 60)
    │
    ├─► Connect to Redis
    │   - Is Redis available?
    │   ├─► YES: Proceed
    │   └─► NO: Log error, allow request (Fail-Open), return
    │
    ├─► Calculate Window
    │   - Current time: 1717594805
    │   - Window size: 60
    │   - Window start: 1717594800
    │   - Reset at: 1717594860
    │
    ├─► Redis Key
    │   - Key: "rate_limit:/api/v1/invoices/upload:192.168.1.100:1717594800"
    │
    ├─► Atomic Increment
    │   - INCR key
    │   - Count: 1, 2, 3, 4, 5, 6, 7...
    │
    ├─► Check Limit
    │   - Count <= max_requests? → ALLOWED
    │   - Count > max_requests? → DENIED
    │
    ├─► If ALLOWED
    │   - Set EXPIRE key 60s
    │   - Call next handler
    │   - Add headers to response
    │   - Return 200-399 response
    │
    └─► If DENIED
        - Return 429 Too Many Requests
        - Attach retry-after header
        - Include error JSON
        - Short-circuit (don't call handler)
```

## Rate Limit State Machine

```
State: "WITHIN_LIMIT"
├─ Condition: used <= max_requests
├─ Action: Allow request
├─ Headers: X-RateLimit-Remaining = max_requests - used
└─ Response: Status 200-399

State: "LIMIT_EXCEEDED"
├─ Condition: used > max_requests
├─ Action: Deny request
├─ Headers: X-RateLimit-Remaining = 0
└─ Response: Status 429

State: "WINDOW_RESET"
├─ Condition: Time > reset_at
├─ Action: Clear counter, reset to state WITHIN_LIMIT
└─ Next request: Starts new window
```

## Redis Data Structure

### Key Format
```
rate_limit:{path}:{client_id}:{window_start}
```

### Examples
```
rate_limit:/api/v1/invoices/upload:192.168.1.100:1717594800
rate_limit:/api/v1/invoices/upload:203.0.113.45:1717594800
rate_limit:/api/v1/components:2001:db8::1:1717594800
```

### Commands Used
```
INCR rate_limit:...           # Atomic increment, creates key if needed
EXPIRE rate_limit:... 60      # Set TTL to 60 seconds (cleanup)
```

### Memory Footprint Example
```
Scenario: 5 endpoints, 10,000 clients per minute

Keys per entry: 1
Memory per key: ~80 bytes (including metadata)
Keys per window: 5 × 10,000 = 50,000
Memory per window: 50,000 × 80 = 4 MB
Total memory (with expiry): ~4 MB (keys expire after 60s)

Minimal impact on Redis cluster.
```

## Configuration Examples

### Example 1: Standard Configuration (Current)
```python
RATE_LIMIT_CONFIG: Dict[str, Tuple[int, int]] = {
    "/api/v1/invoices/upload": (5, 60),       # Heavy LLM endpoint
    "/api/v1/invoices": (20, 60),             # Invoice queries
    "/api/v1/components": (60, 60),           # Standard
    "/api/v1/categories": (60, 60),           # Standard
    "default": (60, 60),                      # Fallback
}
```

### Example 2: Relaxed Configuration (Development)
```python
RATE_LIMIT_CONFIG: Dict[str, Tuple[int, int]] = {
    "/api/v1/invoices/upload": (100, 60),     # Higher for testing
    "/api/v1/invoices": (200, 60),
    "/api/v1/components": (500, 60),
    "/api/v1/categories": (500, 60),
    "default": (1000, 60),
}
```

### Example 3: Strict Configuration (High-Security)
```python
RATE_LIMIT_CONFIG: Dict[str, Tuple[int, int]] = {
    "/api/v1/invoices/upload": (2, 60),       # Very strict
    "/api/v1/invoices": (10, 60),
    "/api/v1/components": (30, 60),
    "/api/v1/categories": (30, 60),
    "default": (30, 60),
}
```

### Example 4: Time-Based Configuration (Per-Hour Limits)
```python
RATE_LIMIT_CONFIG: Dict[str, Tuple[int, int]] = {
    "/api/v1/invoices/upload": (300, 3600),   # 300 per hour
    "/api/v1/invoices": (1200, 3600),         # 1200 per hour
    "/api/v1/components": (3600, 3600),       # 3600 per hour
    "default": (3600, 3600),                  # 3600 per hour
}
```

## Integration Checklist

### ✅ Middleware Registration (AUTO - via add_middleware)
```python
# In src/middleware/__init__.py
def add_middleware(app):
    app.add_middleware(CORSMiddleware, ...)
    app.add_middleware(RateLimitMiddleware)  # ← Added
    app.add_middleware(LoggingAndCorrelationMiddleware)
```

### ✅ Redis Client (AUTO - via lifespan)
```python
# In main.py (already configured)
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis(app)  # ← Redis initialized
    yield
    await close_redis(app)
```

### ✅ No Additional Changes Needed
- No changes to `main.py` required
- No changes to route handlers required
- Works transparently for all endpoints

## Monitoring & Debugging

### Enable Debug Logging

```python
# In main.py or a config module
import logging

logging.getLogger("src.middleware.rate_limit").setLevel(logging.DEBUG)
```

### Log Examples

**Debug Level:**
```
DEBUG Request allowed for client 192.168.1.100 on /api/v1/invoices/upload (used: 3/5)
```

**Warning Level:**
```
WARNING Rate limit exceeded for client 192.168.1.100 on /api/v1/invoices/upload (limit: 5/60s)
```

**Error Level:**
```
ERROR Rate limit check failed for client 192.168.1.100: ConnectionError. Allowing request (fail-safe).
```

### Redis Inspection (for debugging)

```bash
# Connect to Redis
redis-cli

# Check all rate-limit keys
KEYS "rate_limit:*"

# Check count for specific key
GET "rate_limit:/api/v1/invoices/upload:192.168.1.100:1717594800"

# Check TTL
TTL "rate_limit:/api/v1/invoices/upload:192.168.1.100:1717594800"

# Monitor incoming commands (useful for debugging)
MONITOR
```

## Performance Characteristics

### Operation Latency
- **Redis INCR**: ~1ms (local Redis) to ~10ms (network Redis)
- **Redis EXPIRE**: ~0.1ms
- **Total middleware overhead**: ~2-15ms per request (depends on Redis latency)

### Throughput Impact
- **Non-rate-limited request**: Minimal overhead (~2-5%)
- **Rate-limited request (429)**: No downstream processing, saves resources

### Scalability
- **Single Redis instance**: Handles 10,000+ RPS easily
- **Redis Cluster**: Horizontal scaling available
- **Memory**: ~4-5 MB per million unique clients per minute

## Security Considerations

### 1. IP Spoofing Risk

**Problem**: X-Forwarded-For can be spoofed by clients

**Mitigation**:
- Only trust X-Forwarded-For from known proxies
- Validate reverse proxy configuration
- Consider additional rate-limit dimensions (API key, user ID)

```python
# Example: Add user-based rate limiting
def get_client_identifier_with_user(request: Request) -> str:
    # Prefer user ID if authenticated
    user_id = request.headers.get("X-User-ID")
    if user_id:
        return user_id
    # Fall back to IP
    return get_client_identifier(request)
```

### 2. DDoS Limitations

Rate limiting alone is NOT sufficient for DDoS protection:
- Deploy WAF (Web Application Firewall)
- Use CDN with DDoS protection (Cloudflare, AWS Shield)
- Implement infrastructure-level IP blocking
- Monitor for attack patterns

### 3. Redis Security

Ensure Redis is properly secured:
- Require authentication (requirepass in redis.conf)
- Run Redis on private network (not exposed to internet)
- Use TLS for communication (redis-py with ssl=True)
- Regular security updates

```python
# Secure Redis connection example
REDIS_URL = "rediss://password@redis.example.com:6380/0"
# Note: 'rediss://' for TLS encrypted connection
```

## Deployment Examples

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Rate limits can be adjusted via environment if needed
ENV RATE_LIMIT_INVOICES_UPLOAD=5
ENV RATE_LIMIT_INVOICES=20
ENV RATE_LIMIT_DEFAULT=60

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: toolboxdb-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: toolboxdb-api
  template:
    metadata:
      labels:
        app: toolboxdb-api
    spec:
      containers:
      - name: api
        image: toolboxdb-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-credentials
              key: url
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
```

## Testing Strategies

### Unit Tests
```bash
pytest tests/test_rate_limit.py -v
```

### Load Testing (with rate limiting)
```bash
# Using Apache Bench
ab -n 100 -c 10 http://localhost:8000/api/v1/invoices/upload

# Expected: Some requests return 429 after limit exceeded
```

### Integration Testing
```bash
# Test actual Redis behavior
pytest tests/test_rate_limit.py -v --redis-live
```

## Troubleshooting

### Issue: All requests return 429

**Cause**: Extremely low rate limit or wrong calculation
**Solution**:
- Check RATE_LIMIT_CONFIG values
- Verify window_size calculation
- Check Redis for accumulation of keys

### Issue: Rate limit not applied

**Cause**: Redis disconnected, middleware not registered
**Solution**:
- Check Redis connectivity: `redis-cli ping`
- Verify middleware in add_middleware()
- Check logs for "Rate limit check failed"

### Issue: High Redis memory usage

**Cause**: Keys not expiring, or too many unique clients
**Solution**:
- Verify EXPIRE is called
- Check Redis maxmemory policy
- Aggregate clients by subnet instead of individual IP

---

**Last Updated**: June 5, 2026
**Version**: 1.0.0
**Framework**: FastAPI + Uvicorn + Redis
