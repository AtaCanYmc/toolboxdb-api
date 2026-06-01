from fastapi import APIRouter, Depends
from src.db import get_db
from src import models, schemas
from sqlalchemy.orm import Session
from typing import List

category_router = APIRouter(prefix="/api/v1/category", tags=["Category"])


@category_router.get("/", response_model=List[schemas.CategoryResponse])
async def list_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).order_by(models.Category.updated_at.desc()).all()
