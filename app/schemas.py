from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from .enums import QuestionStatus  # ← Changed this line


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)


class DocumentResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str = "healthy"
    message: str = "Service is running"
    
    
class QuestionCreate(BaseModel):
    question: str = Field(..., min_length=1)


class QuestionResponse(BaseModel):
    id: int
    document_id: int
    question: str
    answer: Optional[str] = None
    status: QuestionStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
