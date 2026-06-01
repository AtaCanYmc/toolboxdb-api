from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date


# =====================================================================
# 1. API GİRİŞ / ÇIKIŞ ŞEMALARI (Pydantic Modelleri)
# =====================================================================
# Bu modeller FastAPI'nin istekleri doğrulaması (Validation) ve
# JSON serileştirme işlemleri için kullanılır.

class CategoryBase(BaseModel):
    name: str


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ComponentBase(BaseModel):
    name: str = Field(..., description="Component name")
    quantity: int = Field(0, ge=0, description="Stock quantity")
    category_id: Optional[int] = None
    datasheet_url: Optional[str] = None
    technical_specs: Dict[str, Any] = Field(default_factory=dict, description="JSONB formatted specs")


class ComponentCreate(ComponentBase):
    pass


class ComponentUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = None
    category_id: Optional[int] = None
    datasheet_url: Optional[str] = None
    technical_specs: Optional[Dict[str, Any]] = None


class ComponentResponse(ComponentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceItemBase(BaseModel):
    raw_name: str
    clean_name: Optional[str] = None
    quantity: int
    category: Optional[str] = Field(None, description="AI recomendation category")


class InvoiceItemResponse(InvoiceItemBase):
    id: UUID
    invoice_id: UUID
    is_processed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceBase(BaseModel):
    store_name: str
    invoice_date: Optional[date] = None
    total_amount: Optional[float] = None
    file_path: Optional[str] = None


class InvoiceResponse(InvoiceBase):
    id: UUID
    created_at: datetime
    items: List[InvoiceItemResponse] = []

    class Config:
        from_attributes = True


# =====================================================================
# 2. YAPAY ZEKA (AI) ENTEGRASYON ŞEMALARI
# =====================================================================
# OpenAI Structured Outputs katmanının faturayı tam olarak bu formatta
# parçalamasını zorunlu kılmak için kullanacağımız tipler.

class AIExtractedItem(BaseModel):
    raw_name: str = Field(description="Faturada yazan ham ürün adı")
    clean_name: str = Field(description="Ürünün temizlenmiş net modeli/adı. "
                                        "Örn: 'DHT11' veya '10K Direnç'")
    quantity: int = Field(description="Satın alınan adet")
    category: str = Field(description=("Komponentin uyması gereken kategori: "
                                       "'Mikrodenetleyici', 'Sensör', 'Aktatör', "
                                       "'Görüntü/Ekran', 'Pasif Bileşen', 'Güç/Batarya', "
                                       "'Prototipleme/Kablo'"))


class AIExtractedInvoice(BaseModel):
    store_name: str = Field(description=("Faturanın ait olduğu mağaza: "
                                         "'Direnç.net', 'Robotistan', 'Robolink' veya 'Diğer'"))
    invoice_date: Optional[str] = Field(None, description="Fatura tarihi (YYYY-MM-DD formatında, bulunamazsa null)")
    items: List[AIExtractedItem] = Field(description="Faturadan çıkarılan tüm ürünlerin listesi")


# =====================================================================
# 3. VECTOR DB / RAG ŞEMALARI
# =====================================================================
# Datasheet sorguları ve semantik aramalar için kullanılacak tipler.

class EmbeddingChunk(BaseModel):
    id: Optional[UUID] = None
    component_id: UUID
    content: str
    page_number: Optional[int] = None


class AIProjectSuggestion(BaseModel):
    project_name: str = Field(description="Önerilen projenin adı")
    difficulty: str = Field(description="Zorluk seviyesi: Başlangıç, Orta, İleri")
    wiring_guide: str = Field(description=("Hangi pinin nereye bağlanacağını anlatan "
                                           "net devre şeması taslağı açıklaması"))
    code_sketch: str = Field(description=("Arduino/C++ formatında yazılmış, "
                                          "derlenmeye hazır kod taslağı"))
