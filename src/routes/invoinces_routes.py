from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from src.db import get_db
from src import models, schemas
from sqlalchemy.orm import Session
from pypdf import PdfReader
from src.llm.llm_factory import get_llm_provider
from src.llm.llm_provider import LLMProvider

invoinces_router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])


@invoinces_router.post("/upload", response_model=schemas.InvoiceResponse)
async def upload_and_process_invoice(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        llm: LLMProvider = Depends(get_llm_provider)  # Sihirli entegrasyon noktası
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyaları kabul edilir.")

    # 1. PDF Metnini Oku
    try:
        pdf_reader = PdfReader(file.file)
        full_text = "".join([page.extract_text() + "\n" for page in pdf_reader.pages])
    except Exception:
        raise HTTPException(status_code=400, detail="PDF okunurken bir hata oluştu.")

    if not full_text.strip():
        raise HTTPException(status_code=400, detail="PDF içi boş veya taranmış resim formatında.")

    # 2. Dinamik LLM Provider ile Veri Ayıkla
    try:
        # Hangi modelin çalıştığını router zerre kadar bilmiyor, sadece işini yapıyor!
        ai_data = llm.parse_invoice(full_text, schemas.AIExtractedInvoice)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Analiz hatası ({file.filename}): {str(e)}")

    # 3. Veritabanına Kaydet (Geçici Onay Havuzu)
    db_invoice = models.Invoice(
        store_name=ai_data.store_name,
        invoice_date=ai_data.invoice_date if ai_data.invoice_date else None
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
async def approve_invoice(invoice_id: str, db: Session = Depends(get_db)):
    # İşlenmemiş fatura kalemlerini getir
    items = db.query(models.InvoiceItem).filter(
        models.InvoiceItem.invoice_id == invoice_id,
        models.InvoiceItem.is_processed == False
    ).all()

    if not items:
        raise HTTPException(status_code=404, detail="Onaylanacak işlenmemiş kalem bulunamadı.")

    for item in items:
        # Kategoriyi veritabanında bul veya eşleştir
        category = db.query(models.Category).filter(models.Category.name == item.category_name).first()
        category_id = category.id if category else None

        # Bu parça stokta zaten var mı? (İsim bazlı basit kontrol)
        existing_component = db.query(models.Component).filter(
            models.Component.name == item.clean_name
        ).first()

        if existing_component:
            # Varsa adedi artır
            existing_component.quantity += item.quantity
        else:
            # Yoksa yeni komponent kartı aç
            new_component = models.Component(
                name=item.clean_name,
                quantity=item.quantity,
                category_id=category_id
            )
            db.add(new_component)

        # Kalemi işlendi olarak işaretle
        item.is_processed = True

    db.commit()
    return {"message": f"Faturadaki {len(items)} kalem başarıyla stoğa aktarıldı."}
