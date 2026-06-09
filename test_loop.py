from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        app_instance = self.app
        count = 0
        while hasattr(app_instance, "app"):
            print("Looping app_instance:", type(app_instance))
            app_instance = app_instance.app
            count += 1
            if count > 10:
                print("INFINITE LOOP DETECTED")
                break
        return await call_next(request)

app = FastAPI()
app.add_middleware(RateLimitMiddleware)

from starlette.testclient import TestClient
client = TestClient(app)
try:
    client.get("/")
except Exception as e:
    print(e)
