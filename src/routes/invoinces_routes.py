from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from src import models, schemas
from src.db import get_db
from src.llm.llm_factory import get_llm_provider
from src.llm.llm_provider import LLMProvider
from typing import List

from src.pdf import PDFService
from src.cache import get_redis
from typing import Optional, Any
from src.routes.auth_deps import RoleChecker
from fastapi_i18n import _

invoinces_router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])


# =====================================================================
# 1. MAIN INVOICE OPERATIONS (UPLOAD & APPROVE)
# =====================================================================


@invoinces_router.post("/upload", response_model=schemas.InvoiceResponse)
async def upload_and_process_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
    current_user: models.User = Depends(RoleChecker(["admin", "user"])),
):
    full_text = PDFService.extract_text(file)

    try:
        existing_categories = db.query(models.Category).all()
        category_names = [category.name for category in existing_categories]
        ai_data = llm.parse_invoice(
            full_text, schemas.AIExtractedInvoice, existing_categories=category_names
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_(f"AI Parsing error ({file.filename}): {str(e)}"),
        )

    parsed_date = None
    if ai_data.invoice_date:
        try:
            parsed_date = datetime.strptime(ai_data.invoice_date, "%Y-%m-%d").date()
        except ValueError:
            parsed_date = None

    db_invoice = models.Invoice(
        store_name=ai_data.store_name, invoice_date=parsed_date, user_id=current_user.id
    )
    db.add(db_invoice)
    db.flush()

    for item in ai_data.items:
        db_item = models.InvoiceItem(
            invoice_id=db_invoice.id,
            raw_name=item.raw_name,
            clean_name=item.clean_name,
            quantity=item.quantity,
            category_name=item.category,
        )
        db.add(db_item)

    db.commit()
    db.refresh(db_invoice)
    return db_invoice


@invoinces_router.post("/{invoice_id}/approve")
async def approve_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    redis: Optional[Any] = Depends(get_redis),
    current_user: models.User = Depends(RoleChecker(["admin", "user"])),
):
    # Fetch the invoice to check ownership and get user_id
    query = db.query(models.Invoice).filter(models.Invoice.id == invoice_id)
    if current_user.role != "admin":
        query = query.filter(models.Invoice.user_id == current_user.id)
    invoice = query.first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    if current_user.role != "admin" and invoice.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to approve this invoice."
        )

    items = (
        db.query(models.InvoiceItem)
        .filter(
            models.InvoiceItem.invoice_id == invoice_id,
            models.InvoiceItem.is_processed.is_(False),
        )
        .all()
    )

    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_("No unprocessed items found to approve."),
        )

    # Extract distinct target names
    category_names = {
        item.category_name.lower(): item.category_name
        for item in items
        if item.category_name
    }
    clean_names = {
        item.clean_name.lower(): item.clean_name for item in items if item.clean_name
    }

    # Pre-fetch matching categories and components securely (No raw ilike)
    existing_categories = []
    if category_names:
        existing_categories = (
            db.query(models.Category)
            .filter(func.lower(models.Category.name).in_(category_names.keys()))
            .all()
        )

    existing_components = []
    if clean_names:
        existing_components = (
            db.query(models.Component)
            .filter(func.lower(models.Component.name).in_(clean_names.keys()))
            .all()
        )

    # Build local dictionaries mapping normalized lower-case names to DB objects
    cat_dict = {cat.name.lower(): cat for cat in existing_categories}
    comp_dict = {comp.name.lower(): comp for comp in existing_components}

    created_category = False
    for item in items:
        category_id = None
        if item.category_name:
            item_cat_lower = item.category_name.lower()
            if item_cat_lower in cat_dict:
                category_id = cat_dict[item_cat_lower].id
            else:
                category = models.Category(name=item.category_name)
                db.add(category)
                db.flush()
                cat_dict[item_cat_lower] = category
                category_id = category.id
                created_category = True

        item_comp_lower = item.clean_name.lower()
        if item_comp_lower in comp_dict:
            existing_component = comp_dict[item_comp_lower]
            existing_component.quantity += item.quantity
            if category_id:
                existing_component.category_id = category_id
        else:
            new_component = models.Component(
                name=item.clean_name,
                quantity=item.quantity,
                category_id=category_id,
                user_id=invoice.user_id,
            )
            db.add(new_component)
            comp_dict[item_comp_lower] = new_component

        item.is_processed = True

    db.commit()
    # Invalidate categories cache if we created any new categories
    if redis is not None and created_category:
        try:
            await redis.delete("categories:all")
        except Exception:
            pass

    return {
        "message": _(
            f"Successfully processed {len(items)} items from the invoice and updated inventory stock."
        )
    }


# =====================================================================
# 2. INVOICE QUERY AND MANAGEMENT ENDPOINTS (NEW)
# =====================================================================


@invoinces_router.get("/", response_model=List[schemas.InvoiceResponse])
async def list_invoices(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(RoleChecker(["admin", "user"])),
):
    """List all invoices in the system along with their items."""
    query = db.query(models.Invoice)
    if current_user.role != "admin":
        query = query.filter(models.Invoice.user_id == current_user.id)
    return (
        query.order_by(models.Invoice.created_at.desc()).offset(skip).limit(limit).all()
    )


@invoinces_router.get("/{invoice_id}", response_model=schemas.InvoiceResponse)
async def get_invoice_detail(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["admin", "user"])),
):
    """Fetch all details and items of a specific invoice by ID."""
    query = db.query(models.Invoice).filter(models.Invoice.id == invoice_id)
    if current_user.role != "admin":
        query = query.filter(models.Invoice.user_id == current_user.id)
    invoice = query.first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found."
        )
    return invoice


@invoinces_router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["admin", "user"])),
):
    """Delete the invoice and all its unprocessed items in the approval pool."""
    query = db.query(models.Invoice).filter(models.Invoice.id == invoice_id)
    if current_user.role != "admin":
        query = query.filter(models.Invoice.user_id == current_user.id)
    invoice = query.first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found."
        )

    db.delete(invoice)
    db.commit()
    return None


# =====================================================================
# 3. INVOICE ITEMS MANUAL INTERVENTION ENDPOINTS (NEW)
# =====================================================================


@invoinces_router.put("/items/{item_id}", response_model=schemas.InvoiceItemResponse)
async def update_invoice_item(
    item_id: UUID,
    item_update: schemas.InvoiceItemBase,  # Kullanıcı adı, adet veya kategoriyi düzeltebilir
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["admin", "user"])),
):
    """
    Manually edit an item in the approval pool.
    If the AI extracted the wrong name, you can fix it here before approving.
    """
    db_item = (
        db.query(models.InvoiceItem).filter(models.InvoiceItem.id == item_id).first()
    )
    if not db_item:
        raise HTTPException(status_code=404, detail="Invoice item not found.")

    if current_user.role != "admin" and db_item.invoice.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this item."
        )
        raise HTTPException(status_code=404, detail="Invoice item not found.")

    if current_user.role != "admin" and db_item.invoice.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this item.")

    if db_item.is_processed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_(
                "Cannot modify an item that has already been processed into stock."
            ),
        )

    # Apply fresh incoming data to the model
    update_data = item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)
    return db_item


@invoinces_router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(RoleChecker(["admin", "user"])),
):
    """Completely remove an unwanted or incorrect item from the invoice approval pool."""
    db_item = (
        db.query(models.InvoiceItem).filter(models.InvoiceItem.id == item_id).first()
    )
    if not db_item:
        raise HTTPException(status_code=404, detail="Invoice item not found.")

    if current_user.role != "admin" and db_item.invoice.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this item."
        )
        raise HTTPException(status_code=404, detail="Invoice item not found.")

    if current_user.role != "admin" and db_item.invoice.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this item.")

    if db_item.is_processed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_(
                "Cannot delete an item that has already been processed into stock."
            ),
        )

    db.delete(db_item)
    db.commit()
    return None
