from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from pypdf import PdfReader
from sqlalchemy.orm import Session
from src import models, schemas
from src.db import get_db
from src.llm.llm_factory import get_llm_provider
from src.llm.llm_provider import LLMProvider
from typing import List

invoinces_router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])


# =====================================================================
# 1. FATURA ANA İŞLEMLERİ (UPLOAD & APPROVE)
# =====================================================================

@invoinces_router.post("/upload", response_model=schemas.InvoiceResponse)
async def upload_and_process_invoice(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        llm: LLMProvider = Depends(get_llm_provider)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sadece PDF dosyaları kabul edilir.")

    try:
        pdf_reader = PdfReader(file.file)
        full_text = "".join([page.extract_text() + "\n" for page in pdf_reader.pages])
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PDF okunurken bir hata oluştu.")

    if not full_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="PDF içi boş veya taranmış resim formatında.")

    try:
        ai_data = llm.parse_invoice(full_text, schemas.AIExtractedInvoice)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"AI Analiz hatası ({file.filename}): {str(e)}")

    parsed_date = None
    if ai_data.invoice_date:
        try:
            parsed_date = datetime.strptime(ai_data.invoice_date, "%Y-%m-%d").date()
        except ValueError:
            parsed_date = None

    db_invoice = models.Invoice(
        store_name=ai_data.store_name,
        invoice_date=parsed_date
    )
    db.add(db_invoice)
    db.flush()

    for item in ai_data.items:
        db_item = models.InvoiceItem(
            invoice_id=db_invoice.id,
            raw_name=item.raw_name,
            clean_name=item.clean_name,
            quantity=item.quantity,
            category_name=item.category
        )
        db.add(db_item)

    db.commit()
    db.refresh(db_invoice)
    return db_invoice


@invoinces_router.post("/{invoice_id}/approve")
async def approve_invoice(invoice_id: UUID, db: Session = Depends(get_db)):
    items = db.query(models.InvoiceItem).filter(
        models.InvoiceItem.invoice_id == invoice_id,
        models.InvoiceItem.is_processed == False
    ).all()

    if not items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onaylanacak işlenmemiş kalem bulunamadı.")

    for item in items:
        category_id = None
        if item.category_name:
            category = db.query(models.Category).filter(models.Category.name.ilike(item.category_name)).first()
            if not category:
                category = models.Category(name=item.category_name)
                db.add(category)
                db.flush()
            category_id = category.id

        existing_component = db.query(models.Component).filter(
            models.Component.name.ilike(item.clean_name)
        ).first()

        if existing_component:
            existing_component.quantity += item.quantity
            if category_id:
                existing_component.category_id = category_id
        else:
            new_component = models.Component(
                name=item.clean_name,
                quantity=item.quantity,
                category_id=category_id
            )
            db.add(new_component)

        item.is_processed = True

    db.commit()
    return {"message": f"Faturadaki {len(items)} kalem başarıyla işlendi ve envanter stoğu güncellendi."}


# =====================================================================
# 2. FATURA SORGULAMA VE YÖNETİM ENDPOINT'LERİ (YENİ)
# =====================================================================

@invoinces_router.get("/", response_model=List[schemas.InvoiceResponse])
async def list_invoices(
        db: Session = Depends(get_db),
        skip: int = 0,
        limit: int = 50
):
    """Sistemdeki tüm faturaları içindeki kalemlerle birlikte listeler."""
    return db.query(models.Invoice).order_by(models.Invoice.created_at.desc()).offset(skip).limit(limit).all()


@invoinces_router.get("/{invoice_id}", response_model=schemas.InvoiceResponse)
async def get_invoice_detail(invoice_id: UUID, db: Session = Depends(get_db)):
    """ID bazlı tek bir faturanın tüm detaylarını ve kalemlerini getirir."""
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fatura bulunamadı.")
    return invoice


@invoinces_router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(invoice_id: UUID, db: Session = Depends(get_db)):
    """Faturayı ve faturaya ait onay havuzundaki işlenmemiş tüm kalemleri siler."""
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fatura bulunamadı.")

    db.delete(invoice)
    db.commit()
    return None


# =====================================================================
# 3. FATURA KALEMLERİ MANUEL MÜDAHALE ENDPOINT'LERİ (YENİ)
# =====================================================================

@invoinces_router.put("/items/{item_id}", response_model=schemas.InvoiceItemResponse)
async def update_invoice_item(
        item_id: UUID,
        item_update: schemas.InvoiceItemBase,  # Kullanıcı adı, adet veya kategoriyi düzeltebilir
        db: Session = Depends(get_db)
):
    """
    Onay havuzundaki bir kalemi manuel düzenler.
    AI yanlış isim çıkardıysa onaylamadan önce buradan düzeltebilirsin.
    """
    db_item = db.query(models.InvoiceItem).filter(models.InvoiceItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fatura kalemi bulunamadı.")

    if db_item.is_processed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Stoğa işlenmiş bir kalemi değiştiremezsiniz.")

    # Gelen taze verileri modele yediriyoruz
    update_data = item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)
    return db_item


@invoinces_router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice_item(item_id: UUID, db: Session = Depends(get_db)):
    """Faturadaki istemediğin veya hatalı bir kalemi onay havuzundan tamamen uçurur."""
    db_item = db.query(models.InvoiceItem).filter(models.InvoiceItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fatura kalemi bulunamadı.")

    if db_item.is_processed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stoğa işlenmiş bir kalemi silemezsiniz.")

    db.delete(db_item)
    db.commit()
    return None
