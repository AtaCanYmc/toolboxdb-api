# Redis Caching Setup & Quick Start Guide

## 🎯 Overview

The ToolboxDB API now includes production-ready **Redis caching** for the category list endpoint. This guide walks you through setup, configuration, and testing.

---

## 📦 Prerequisites

- **Docker** (for local Redis)
- **Python 3.9+** with venv
- **redis-py 4.6.0+** (included in requirements.txt)

---

## 🚀 Setup Instructions

### Step 1: Start Redis

#### Option A: Docker (Recommended)

```bash
# Start Redis container
docker run -d \
  --name toolbox-redis \
  -p 6379:6379 \
  redis:7-alpine

# Verify it's running
docker logs toolbox-redis
# Output: "Ready to accept connections"
```

#### Option B: Homebrew (macOS)

```bash
brew install redis
redis-server
```

#### Option C: Manual (Any OS)

Download from https://redis.io/download and run `redis-server`.

### Step 2: Configure Environment

Create/update `.env` file:

```bash
# .env
REDIS_URL=redis://localhost:6379/0
APP_TITLE=ToolboxDB API
DATABASE_URL=postgresql://user:pass@host:5432/toolboxdb
```

If no `.env` is present, defaults are used:
- `REDIS_URL` defaults to `redis://localhost:6379/0`
- If Redis is unreachable, the app gracefully falls back to database-only mode

### Step 3: Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Run the Application

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

You should see output like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Connecting to database and creating tables if they don't exist...
INFO:     Database tables initialized successfully!
INFO:     Redis client initialized.
```

---

## ✅ Verify Redis Integration

### Check Redis Connection

```bash
# In a new terminal, test Redis CLI
redis-cli ping
# Response: PONG

redis-cli
> KEYS *
# Should show: "categories:all" (after first API call)
```

### Test Cache via API

```bash
# 1. First request (cache miss)
curl -s http://127.0.0.1:8000/api/v1/category/ | jq .

# Behind the scenes:
# - API queries database
# - Result is cached in Redis under key "categories:all"
# - Next requests will hit Redis instead

# 2. Second request (cache hit)
curl -s http://127.0.0.1:8000/api/v1/category/ | jq .
# Faster response (from Redis, not database)

# 3. Create a new category (cache invalidation)
curl -X POST http://127.0.0.1:8000/api/v1/category/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Sensörler"}'

# Behind the scenes:
# - Category saved to database
# - Redis cache key "categories:all" is deleted
# - Next GET request rebuilds cache from updated database

# 4. Verify cache was rebuilt
curl -s http://127.0.0.1:8000/api/v1/category/ | jq .
# New category is now visible and cached
```

### Monitor Redis in Real-Time

```bash
# Open Redis CLI in a terminal
redis-cli

# Watch all commands in real-time
> MONITOR

# In another terminal, make API calls
# You'll see Redis operations like:
# 1) "GET" "categories:all"
# 2) "SET" "categories:all" "{...json...}"
# 3) "DEL" "categories:all"
```

---

## 🔄 Cache Behavior

### When Cache is Used

| Endpoint | Method | Cache Behavior |
|----------|--------|-----------------|
| `/api/v1/category/` | GET | ✅ **READ**: Check Redis first, fall back to DB if miss |
| `/api/v1/category/search` | GET | ❌ **NOT CACHED**: Always query fresh from DB |
| `/api/v1/category/` | POST | ✅ **INVALIDATE**: Delete `categories:all` after commit |
| `/api/v1/category/{id}` | PUT | ✅ **INVALIDATE**: Delete `categories:all` after commit |
| `/api/v1/category/{id}` | DELETE | ✅ **INVALIDATE**: Delete `categories:all` after commit |
| `/api/v1/invoices/{id}/approve` | POST | ✅ **INVALIDATE**: If new category created, delete cache |

### Why These Choices?

- **Category List is Cached:** Reference data, rarely changes, high read volume
- **Search is NOT Cached:** Dynamic queries, low hit rate, better to query DB
- **Component Inventory is NOT Cached:** Quantities update frequently (invoice approval), cache would be stale
- **Cache Invalidation:** On every write operation, cache is proactively deleted (no TTL staleness)

---

## 🛡️ Error Handling & Resilience

### Redis Unavailable

If Redis is down or unreachable:

```
INFO: Connecting to Redis...
WARNING: Redis connection failed, continuing without cache
# API works normally, queries go directly to database
```

The system is **fault-tolerant**: Redis failures don't break the API.

### Check API Health

```bash
curl http://127.0.0.1:8000/health
# Response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "redis": "connected"  # or "disconnected"
# }
```

---

## 🧪 Performance Testing

### Measure Cache Efficiency

```bash
# Install Apache Bench (if not present)
# macOS: brew install httpd
# Linux: apt-get install apache2-utils

# Warm up cache
curl -s http://127.0.0.1:8000/api/v1/category/ > /dev/null

# Measure cache hits (should be very fast)
ab -n 1000 -c 10 http://127.0.0.1:8000/api/v1/category/

# Expected output:
# Requests per second: 500+ (cache hits)
# vs
# Requests per second: 50-100 (database queries)
```

### Monitor Database Load

```bash
# Before caching: Every request hits the database
# After caching: Only writes go to database, reads hit Redis

# Check in PostgreSQL logs or use monitoring tool:
SELECT * FROM pg_stat_statements WHERE query LIKE '%categories%';
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Redis connection URL (default: redis://localhost:6379/0)
REDIS_URL=redis://localhost:6379/0

# Redis password (if required)
REDIS_PASSWORD=your-redis-password

# Redis database number (default: 0)
# Useful for separating dev/staging/prod caches
REDIS_DB=0
```

### Customizing Cache Behavior

Edit `src/cache.py` to adjust:

```python
# Increase timeout (default: NaN, auto-timeout)
await redis.set(cache_key, json.dumps(payload), ex=86400)  # 24 hours

# Use namespaced keys for multitenancy
cache_key = f"org:{org_id}:categories:all"

# Add custom TTL logic
if is_production:
    await redis.set(..., ex=3600)  # 1 hour
else:
    await redis.set(..., ex=None)  # No expiry
```

---

## 🐛 Troubleshooting

### Problem: "Cannot connect to Redis"

```
Solution: 
1. Verify Redis is running: redis-cli ping
2. Check REDIS_URL in .env
3. Check firewall (port 6379 open)
4. Try: docker logs toolbox-redis
```

### Problem: Cache seems stale after update

```
Solution:
1. Cache should invalidate automatically on create/update/delete
2. Verify in Redis: redis-cli DEL categories:all
3. Hit API again to rebuild cache
4. Check logs for cache invalidation messages
```

### Problem: High memory usage in Redis

```
Solution:
1. For now, only `categories:all` is cached (small footprint)
2. If issue persists, check Redis size: redis-cli INFO memory
3. Consider TTL if datasets grow large: ex=86400 (1 day)
4. Use redis-cli KEYS * to see all cached items
```

### Problem: SQLAlchemy Type Warnings

```
Solution: These are IDE type-checker warnings, not runtime errors.
SQLAlchemy's ORM filter() has complex type hints that IDEs struggle with.
The code runs fine. You can ignore these warnings.
```

---

## 📊 Monitoring & Logging

### Enable Debug Logging

Edit `main.py` to enable Redis operation logs:

```python
import logging
logging.basicConfig(level=logging.DEBUG)  # More verbose

# Now you'll see:
# INFO:src.cache:Redis ping successful
# DEBUG:src.cache:Cache HIT for categories:all
# DEBUG:src.cache:Cache SET categories:all
# DEBUG:src.cache:Cache DEL categories:all
```

### Redis Stats

```bash
redis-cli INFO stats
# Shows: total_commands_processed, total_connections_received, etc.

redis-cli --stat
# Real-time stats monitor
```

---

## 🚀 Production Deployment

### Docker Compose (Full Stack)

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: ..
    ports:
      - "8000:8000"
    environment:
      REDIS_URL: redis://redis:6379/0
      DATABASE_URL: postgresql://user:pass@postgres:5432/toolboxdb
    depends_on:
      - redis
      - postgres

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  redis_data:
  postgres_data:
```

Run: `docker-compose up`

### Kubernetes Deployment

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: toolbox-config
data:
  REDIS_URL: "redis://redis-service:6379/0"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: toolbox-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: toolboxdb-api:latest
        envFrom:
        - configMapRef:
            name: toolbox-config
        ports:
        - containerPort: 8000
```

---

## 📞 Quick Reference

| Task | Command |
|------|---------|
| Start Redis (Docker) | `docker run -d -p 6379:6379 redis:7-alpine` |
| Start API | `uvicorn main:app --reload` |
| Check Redis | `redis-cli ping` |
| View Cache | `redis-cli GET categories:all` |
| Clear Cache | `redis-cli DEL categories:all` |
| Monitor | `redis-cli MONITOR` |
| API Docs | http://127.0.0.1:8000/docs |
| Health Check | `curl http://127.0.0.1:8000/health` |

---

## 🎓 Learning Resources

- **Redis Official:** https://redis.io/docs/
- **FastAPI Lifespan:** https://fastapi.tiangolo.com/advanced/events/
- **SQLAlchemy ORM:** https://docs.sqlalchemy.org/
- **redis-py Async:** https://github.com/redis/redis-py

---

**Status:** ✅ Ready for Development & Production

*Last Updated: June 5, 2026*

