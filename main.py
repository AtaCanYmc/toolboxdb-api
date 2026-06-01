import logging
import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from src import models
from src.db import db_connector
from src.middleware import add_middleware
from src.routes import add_routes

# Load .env file if present. Use DOTENV_PATH to override if needed.
dotenv_path = os.getenv("DOTENV_PATH")
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    load_dotenv()

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
RELOAD = os.getenv("RELOAD", "TRUE").upper() == "TRUE"

logger.info("Connecting to database and creating tables if they don't exist...")
try:
    models.Base.metadata.create_all(bind=db_connector.engine)
    logger.info("Database tables initialized successfully!")
except Exception as e:
    logger.error(f"Database initialization failed: {str(e)}")
    raise e

app = FastAPI(title="Akıllı Komponent Yönetimi - Prototip")
add_middleware(app)
add_routes(app)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        log_level="info"
    )
