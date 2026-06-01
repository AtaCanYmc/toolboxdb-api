from fastapi import APIRouter, Depends, HTTPException, status
from src.db import get_db
from src import models, schemas
from sqlalchemy.orm import Session
from typing import List

category_router = APIRouter(prefix="/api/v1/category", tags=["Category"])


@category_router.get("/", response_model=List[schemas.CategoryResponse])
async def list_categories(
        db: Session = Depends(get_db),
        skip: int = 0,
        limit: int = 100
):
    query = db.query(models.Category)
    return query.order_by(models.Category.id.desc()).offset(skip).limit(limit).all()


@category_router.get("/search", response_model=List[schemas.CategoryResponse])
async def search_categories(
        db: Session = Depends(get_db),
        search: str = "",
        skip: int = 0,
        limit: int = 100
):
    if len(search.strip()) == 0:
        return []

    query = db.query(models.Category)
    query = query.filter(models.Category.name.ilike(f"%{search}%"))

    return query.order_by(models.Category.updated_at.desc()).offset(skip).limit(limit).all()


@category_router.post("/", response_model=schemas.CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
        category: schemas.CategoryBase,  # name alanını içerir
        db: Session = Depends(get_db)
):
    # Aynı isimde kategori var mı kontrolü (Bonus: mükerrer kayıtları önler)
    existing_category = db.query(models.Category).filter(models.Category.name.ilike(category.name)).first()
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu isimde bir kategori zaten mevcut."
        )

    db_category = models.Category(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@category_router.put("/{category_id}", response_model=schemas.CategoryResponse)
async def update_category(
        category_id: int,
        category_update: schemas.CategoryBase,
        db: Session = Depends(get_db)
):
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Kategori bulunamadı.")

    db_category.name = category_update.name

    db.commit()
    db.refresh(db_category)
    return db_category


@category_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: int, db: Session = Depends(get_db)):
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Kategori bulunamadı.")

    db.delete(db_category)
    db.commit()
    return None
