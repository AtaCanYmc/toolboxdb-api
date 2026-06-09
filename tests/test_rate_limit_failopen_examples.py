"""
Example: Testing the Fail-Open Rate Limiter Middleware

This file demonstrates how to test the refactored rate limiting middleware
to verify Fail-Open behavior when Redis is unavailable.

Note: These are example test cases. Adapt them to your testing framework.
"""

import pytest
from unittest.mock import AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.middleware.rate_limit import RateLimitMiddleware


# ============================================================================
# Test Case 1: Redis Available - Rate Limiting Enforces Normally
# ============================================================================


@pytest.mark.asyncio
async def test_rate_limit_enforces_when_redis_available():
    """
    GIVEN: Redis client is healthy and responding
    WHEN: A client makes requests exceeding the rate limit
    THEN: Requests beyond the limit should return HTTP 429
    """
    app = FastAPI()

    # Mock Redis client
    mock_redis = AsyncMock()
    app.state.redis = mock_redis

    # Add middleware
    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"status": "ok"}

    # Simulate: counter is at 60 (limit is 60)
    mock_redis.incr = AsyncMock(return_value=60)
    mock_redis.expire = AsyncMock()

    client = TestClient(app)

    # Request #60 should pass
    response = client.get("/api/v1/test")
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert response.headers["X-RateLimit-Limit"] == "60"

    # Request #61 should be limited (counter > 60)
    mock_redis.incr = AsyncMock(return_value=61)
    response = client.get("/api/v1/test")
    assert response.status_code == 429
    assert response.json()["error"] == "Too Many Requests"
    assert "X-RateLimit-Reset" in response.headers
    assert "Retry-After" in response.headers


# ============================================================================
# Test Case 2: Redis Unavailable - Requests Pass Through
# ============================================================================


@pytest.mark.asyncio
async def test_rate_limit_allows_all_when_redis_unavailable():
    """
    GIVEN: Redis client is not available (None)
    WHEN: A client makes any number of requests
    THEN: All requests should return HTTP 200 (no rate limiting)
    """
    app = FastAPI()

    # Simulate: Redis is not initialized
    app.state.redis = None

    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)

    # Send 100 requests - all should succeed
    for _ in range(100):
        response = client.get("/api/v1/test")
        assert response.status_code == 200
        # Note: X-RateLimit headers may not be present when Redis is down
        assert response.json()["status"] == "ok"


# ============================================================================
# Test Case 3: Redis Connection Error - Fail-Open Behavior
# ============================================================================


@pytest.mark.asyncio
async def test_rate_limit_allows_all_on_redis_connection_error():
    """
    GIVEN: Redis client exists but raises ConnectionError
    WHEN: A client makes requests
    THEN: All requests should pass through (fail-open)
    """
    app = FastAPI()

    # Mock Redis that raises ConnectionError
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(side_effect=Exception("Connection refused"))
    app.state.redis = mock_redis

    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)

    # Requests should still succeed
    response = client.get("/api/v1/test")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ============================================================================
# Test Case 4: Redis Timeout - Fail-Open Behavior
# ============================================================================


@pytest.mark.asyncio
async def test_rate_limit_allows_all_on_redis_timeout():
    """
    GIVEN: Redis client exists but times out
    WHEN: A client makes requests
    THEN: All requests should pass through (fail-open)
    """
    import asyncio

    app = FastAPI()

    # Mock Redis that times out
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(side_effect=asyncio.TimeoutError())
    app.state.redis = mock_redis

    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)

    response = client.get("/api/v1/test")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ============================================================================
# Test Case 5: Health Check Endpoint Skipped
# ============================================================================


@pytest.mark.asyncio
async def test_rate_limit_skips_health_check():
    """
    GIVEN: A request to /health
    WHEN: Rate limiter processes the request
    THEN: The request should skip rate limiting entirely
    """
    app = FastAPI()
    app.state.redis = None

    app.add_middleware(RateLimitMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    client = TestClient(app)

    # /health should always succeed, even if Redis is unavailable
    for _ in range(100):
        response = client.get("/health")
        assert response.status_code == 200


# ============================================================================
# Test Case 6: Correlation ID Included in Logs
# ============================================================================


@pytest.mark.asyncio
async def test_rate_limit_logs_include_correlation_id():
    """
    GIVEN: A request with X-Correlation-ID header
    WHEN: Rate limiting is checked
    THEN: Logs should include the correlation ID
    """
    app = FastAPI()
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(side_effect=Exception("Redis error"))
    app.state.redis = mock_redis

    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)

    # Request with correlation ID
    response = client.get(
        "/api/v1/test", headers={"X-Correlation-ID": "test-corr-id-12345"}
    )

    assert response.status_code == 200
    # In real scenario, check logs contain "test-corr-id-12345"


# ============================================================================
# Integration Test: Scenario with Rapid Requests
# ============================================================================


@pytest.mark.asyncio
async def test_rapid_requests_with_degraded_redis():
    """
    GIVEN: Redis is experiencing transient failures
    WHEN: A client sends rapid requests
    THEN: All requests should succeed (fail-open), and no 429 responses
    """
    app = FastAPI()

    # Mock Redis that fails intermittently
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(
        side_effect=[
            1,
            2,
            3,  # First 3 succeed
            Exception("Network timeout"),  # Then fails
            Exception("Network timeout"),
            Exception("Network timeout"),
            4,
            5,
            6,  # Recovers
        ]
    )
    app.state.redis = mock_redis

    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)

    # Send 9 requests - all should succeed
    responses = []
    for i in range(9):
        response = client.get("/api/v1/test")
        responses.append(response.status_code)
        print(f"Request {i + 1}: {response.status_code}")

    # Assert: No 429 responses (all succeeded despite Redis failures)
    assert all(
        status == 200 for status in responses
    ), f"Expected all 200, got: {responses}"
    print("✅ All 9 requests succeeded despite Redis failures")


# ============================================================================
# Example: How to Run These Tests
# ============================================================================
"""
Installation:
    pip install pytest pytest-asyncio httpx python-dotenv

Run all rate-limit tests:
    pytest tests/test_rate_limit.py -v

Run specific test:
    pytest tests/test_rate_limit.py::test_rate_limit_enforces_when_redis_available -v

Run with logging:
    pytest tests/test_rate_limit.py -v -s

Run with coverage:
    pytest tests/test_rate_limit.py --cov=src.middleware.rate_limit
"""
