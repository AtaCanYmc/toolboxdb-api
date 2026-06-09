from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date
import re


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
    technical_specs: Dict[str, Any] = Field(
        default_factory=dict, description="JSONB formatted specs"
    )


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

    @model_validator(mode="after")
    def fix_package_quantity(self) -> "InvoiceItemBase":
        match = re.search(r"(\d+)\s*(?:adet|li|lu|lü|lı|pack|x)", self.raw_name.lower())

        if match:
            extracted_multiplier = int(match.group(1))
            if self.quantity == 1 and extracted_multiplier > 1:
                self.quantity = extracted_multiplier

        return self


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
    clean_name: str = Field(
        description="Ürünün temizlenmiş net modeli/adı. "
        "Örn: 'DHT11' veya '10K Direnç'"
    )
    quantity: int = Field(description="Satın alınan adet")
    category: str = Field(
        description=(
            "Komponentin uyması gereken kategori: "
            "'Mikrodenetleyici', 'Sensör', 'Aktatör', "
            "'Görüntü/Ekran', 'Pasif Bileşen', 'Güç/Batarya', "
            "'Prototipleme/Kablo'"
        )
    )


class AIExtractedInvoice(BaseModel):
    store_name: str = Field(
        description=(
            "Faturanın ait olduğu mağaza: "
            "'Direnç.net', 'Robotistan', 'Robolink' veya 'Diğer'"
        )
    )
    invoice_date: Optional[str] = Field(
        None, description="Fatura tarihi (YYYY-MM-DD formatında, bulunamazsa null)"
    )
    items: List[AIExtractedItem] = Field(
        description="Faturadan çıkarılan tüm ürünlerin listesi"
    )


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
    wiring_guide: str = Field(
        description=(
            "Hangi pinin nereye bağlanacağını anlatan "
            "net devre şeması taslağı açıklaması"
        )
    )
    code_sketch: str = Field(
        description=("Arduino/C++ formatında yazılmış, " "derlenmeye hazır kod taslağı")
    )


# =====================================================================
# Suggestion
# =====================================================================


class ProjectSuggestionRequest(BaseModel):
    extra_components: List[str] = Field(
        default=[],
        description="Stokta olmayıp kullanıcının manuel eklemek istediği ekstra parçalar",
    )
    difficulty_level: str = Field(
        default="Medium",
        description="Proje zorluk seviyesi: Beginner, Medium, Advanced",
    )
    extra_message: str | None = Field(
        default=None,
        description=(
            "Kullanıcının yapay zekaya iletmek istediği özel not veya tema"
            " (Örn: Sadece akıllı ev olsun)"
        ),
    )


class NeededComponent(BaseModel):
    name: str = Field(description="Komponentin temiz adı")
    status: str = Field(
        description="Elinde 'Mevcut' mu yoksa dışarıdan 'Satın Alınmalı' mı?"
    )


class ProjectIdea(BaseModel):
    title: str = Field(description="Projenin havalı adı")
    description: str = Field(
        description=(
            "Projenin 5-10 cümlelik kısa özeti ve ne işe yaradığı. "
            "Parçaların tam olarak ne işe yaradığı açıkça söylenmeli"
        )
    )
    difficulty: str = Field(description="Belirlenen zorluk seviyesi")
    components_breakdown: List[NeededComponent] = Field(
        description="Proje için gereken tüm parçalar ve stok durumları"
    )
    estimated_build_time_hours: int = Field(description="Tahmini yapım süresi (saat)")
    step_by_step_summary: List[str] = Field(
        description="Projenin yapım aşamalarının kısa ama açıklayıcı özeti"
    )


class ProjectSuggestionResponse(BaseModel):
    ideas: List[ProjectIdea] = Field(
        description="Üretilen yaratıcı proje fikirleri listesi"
    )
