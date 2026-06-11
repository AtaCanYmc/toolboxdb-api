import logging
import os
import uvicorn
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from src.middleware import add_middleware
from src.routes import add_routes
from src.cache import init_redis, close_redis
from fastapi_i18n import i18n

# Load .env file if present. Use DOTENV_PATH to override if needed.
dotenv_path = os.getenv("DOTENV_PATH")
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    load_dotenv()

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App configuration
APP_TITLE = os.getenv("APP_TITLE", "toolbox backend")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
RELOAD = os.getenv("RELOAD", "TRUE").upper() == "TRUE"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup initialization and shutdown cleanup.

    Startup (before yield):
     - Initialize database tables
     - Initialize Redis client

    Shutdown (after yield):
     - Close Redis connection
    """
    # ==================== STARTUP ====================
    logger.info("Database connection established. Migrations are managed by Alembic.")

    # Initialize Redis client
    try:
        await init_redis(app)
        logger.info("Redis initialized successfully!")
    except Exception as e:
        logger.error(f"Redis initialization failed: {str(e)}")

    yield
    # ==================== SHUTDOWN ====================
    logger.info("Shutting down: closing Redis connection...")
    await close_redis(app)
    logger.info("Redis connection closed. Shutdown complete.")


app = FastAPI(title=APP_TITLE, lifespan=lifespan, dependencies=[Depends(i18n)])
add_middleware(app)
add_routes(app)

if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=RELOAD, log_level="info")
