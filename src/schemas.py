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


class UserRegister(BaseModel):
    username: str = Field(..., description="Unique username")
    email: str = Field(..., description="User's email address")
    password: str = Field(..., min_length=6, description="Plain text password")
    role: str = Field("user", description="User role: admin, user, chatter")


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceItemBase(BaseModel):
    raw_name: str
    clean_name: Optional[str] = None
    quantity: int
    category: Optional[str] = Field(None, description="AI recommendation category")

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
    user_id: int
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
    raw_name: str = Field(description="Raw product name on the invoice")
    clean_name: str = Field(
        description="Cleaned exact model/name of the product. "
        "E.g.: 'DHT11' or '10K Resistor'"
    )
    quantity: int = Field(description="Purchased quantity")
    category: str = Field(
        description=(
            "Category the component belongs to: "
            "'Microcontroller', 'Sensor', 'Actuator', "
            "'Display/Screen', 'Passive Component', 'Power/Battery', "
            "'Prototyping/Cable'"
        )
    )


class AIExtractedInvoice(BaseModel):
    store_name: str = Field(
        description=(
            "Store of the invoice: " "'Direnç.net', 'Robotistan', 'Robolink' or 'Other'"
        )
    )
    invoice_date: Optional[str] = Field(
        None, description="Invoice date (YYYY-MM-DD format, null if not found)"
    )
    items: List[AIExtractedItem] = Field(
        description="List of all products extracted from the invoice"
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
    project_name: str = Field(description="Name of the suggested project")
    difficulty: str = Field(description="Difficulty level: Beginner, Medium, Advanced")
    wiring_guide: str = Field(
        description=(
            "Clear circuit diagram draft explaining " "which pin connects where"
        )
    )
    code_sketch: str = Field(
        description=("Ready-to-compile code sketch " "written in Arduino/C++ format")
    )


# =====================================================================
# Suggestion
# =====================================================================


class ProjectSuggestionRequest(BaseModel):
    extra_components: List[str] = Field(
        default=[],
        description="Extra parts the user wants to add manually that are not in stock",
    )
    difficulty_level: str = Field(
        default="Medium",
        description="Project difficulty level: Beginner, Medium, Advanced",
    )
    extra_message: str | None = Field(
        default=None,
        description=(
            "Special note or theme the user wants to convey to the AI"
            " (E.g.: Only smart home projects)"
        ),
    )


class ProjectDetailRequest(BaseModel):
    project_title: str = Field(description="Name of the project to detail")
    project_description: str = Field(description="Short summary of the project")
    difficulty: str = Field(description="Difficulty level of the project")
    components: List[str] = Field(
        description="Names of the components to be included in the project"
    )


class NeededComponent(BaseModel):
    name: str = Field(description="Clean name of the component")
    status: str = Field(
        description="Is it 'Available' in stock or 'To Buy' from outside?"
    )


class ProjectIdea(BaseModel):
    title: str = Field(description="Cool name of the project")
    description: str = Field(
        description=(
            "Short 5-10 sentence summary of the project and its purpose. "
            "The exact purpose of the parts should be clearly stated"
        )
    )
    difficulty: str = Field(description="Determined difficulty level")
    components_breakdown: List[NeededComponent] = Field(
        description="All required parts for the project and their stock statuses"
    )
    estimated_build_time_hours: int = Field(description="Estimated build time (hours)")
    step_by_step_summary: List[str] = Field(
        description="Short but explanatory summary of the project's build steps"
    )


class ProjectSuggestionResponse(BaseModel):
    ideas: List[ProjectIdea] = Field(
        description="List of generated creative project ideas"
    )
