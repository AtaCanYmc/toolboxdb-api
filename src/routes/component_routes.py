from fastapi import APIRouter, Depends
from src.db import get_db
from src import models, schemas
from sqlalchemy.orm import Session
from typing import List

component_router = APIRouter(prefix="/api/v1/components", tags=["Components"])


@component_router.get("/", response_model=List[schemas.ComponentResponse])
async def list_components(db: Session = Depends(get_db)):
    return db.query(models.Component).order_by(models.Component.updated_at.desc()).all()
