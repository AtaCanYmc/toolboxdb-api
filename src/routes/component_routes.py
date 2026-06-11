from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from src.db import get_db
from src import models, schemas
from sqlalchemy.orm import Session
from typing import List
from src.routes.auth_deps import get_current_user
from sqlalchemy import or_

component_router = APIRouter(prefix="/api/v1/components", tags=["Components"])


@component_router.get("/", response_model=List[schemas.ComponentResponse])
async def list_components(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
):
    query = db.query(models.Component).filter(
        models.Component.user_id == current_user.id
    )
    return (
        query.order_by(models.Component.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@component_router.get("/search", response_model=List[schemas.ComponentResponse])
async def search_components(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    search: str = "",
    skip: int = 0,
    limit: int = 100,
):
    if len(search.strip()) == 0:
        return []
    # Search component by its name or its category name (case-insensitive)
    query = db.query(models.Component).outerjoin(models.Category)
    query = query.filter(models.Component.user_id == current_user.id)
    query = query.filter(
        or_(
            models.Component.name.ilike(f"%{search}%"),
            models.Category.name.ilike(f"%{search}%"),
        )
    )

    return (
        query.order_by(models.Component.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@component_router.post(
    "/", response_model=schemas.ComponentResponse, status_code=status.HTTP_201_CREATED
)
async def create_component(
    component: schemas.ComponentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    component_data = component.model_dump()
    component_data["user_id"] = current_user.id
    db_component = models.Component(**component_data)
    db.add(db_component)
    db.commit()
    db.refresh(db_component)
    return db_component


@component_router.put("/{component_id}", response_model=schemas.ComponentResponse)
async def update_component(
    component_id: UUID,
    component_update: schemas.ComponentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_component = (
        db.query(models.Component)
        .filter(models.Component.id == component_id)
        .filter(models.Component.user_id == current_user.id)
        .first()
    )

    if not db_component:
        raise HTTPException(status_code=404, detail="Component not found")

    update_data = component_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_component, key, value)

    db.commit()
    db.refresh(db_component)
    return db_component


@component_router.delete("/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_component(
    component_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_component = (
        db.query(models.Component)
        .filter(models.Component.id == component_id)
        .filter(models.Component.user_id == current_user.id)
        .first()
    )

    if not db_component:
        raise HTTPException(status_code=404, detail="Component not found.")

    db.delete(db_component)
    db.commit()
    return None
