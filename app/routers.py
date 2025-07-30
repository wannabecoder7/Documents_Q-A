from fastapi import APIRouter, HTTPException, Depends, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
import asyncio
import logging
from fastapi import UploadFile, File
import PyPDF2, docx, io

from .database import get_db
from .models import Document, Question
from .enums import QuestionStatus
from .schemas import (
    DocumentCreate, 
    DocumentResponse, 
    QuestionCreate, 
    QuestionResponse
)
# Removed the services import since we're not using them

# Configure logging
logger = logging.getLogger(__name__)

# Background task storage for tracking async operations
background_tasks = {}

# Create routers for different resource groups
documents_router = APIRouter(prefix="/documents", tags=["documents"])
questions_router = APIRouter(prefix="/questions", tags=["questions"])
health_router = APIRouter(prefix="/health", tags=["health"])

async def process_question_async(question_id: int, question_text: str, db_session_factory):
    """
    Async background task to simulate LLM processing.
    """
    try:
        logger.info(f"Starting background processing for question {question_id}")
        
        # Simulate LLM processing time
        await asyncio.sleep(5)
        
        # Generate dummy LLM response
        answer = f"This is a generated answer to your question: {question_text}"
        
        # Update question with answer using a new database session
        async with db_session_factory() as db:
            try:
                # Get the question
                result = await db.execute(
                    select(Question).where(Question.id == question_id)
                )
                question = result.scalar_one_or_none()
                
                if question:
                    question.answer = answer
                    question.status = QuestionStatus.ANSWERED.value
                    await db.commit()
                    logger.info(f"Successfully processed question {question_id}")
                else:
                    logger.error(f"Failed to update question {question_id} - not found")
            except Exception as db_error:
                await db.rollback()
                logger.error(f"Database error updating question {question_id}: {str(db_error)}")
                raise
                
        # Remove from background tasks
        if question_id in background_tasks:
            del background_tasks[question_id]
            
    except Exception as e:
        logger.error(f"Error processing question {question_id}: {str(e)}")
        
        # Update status to error
        try:
            async with db_session_factory() as db:
                result = await db.execute(
                    select(Question).where(Question.id == question_id)
                )
                question = result.scalar_one_or_none()
                
                if question:
                    question.status = QuestionStatus.ERROR.value
                    await db.commit()
        except Exception as update_error:
            logger.error(f"Failed to update error status: {str(update_error)}")
        
        # Remove from background tasks
        if question_id in background_tasks:
            del background_tasks[question_id]

# Document endpoints
@documents_router.post(
    "/", 
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new document",
    description="Upload a document with title and content for Q&A processing"
)
async def upload_document(
    title: str = Form(..., description="Document title", min_length=1, max_length=255),
    content: str = Form(..., description="Document content", min_length=1),
    db: AsyncSession = Depends(get_db)
) -> DocumentResponse:
    """Upload a new document to the system."""
    try:
        document_data = DocumentCreate(title=title, content=content)
        
        # Create document directly if service doesn't exist
        document = Document(
            title=document_data.title,
            content=document_data.content
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        logger.info(f"Document created successfully: {document.id}")
        return DocumentResponse.model_validate(document)
        
    except Exception as e:
        logger.error(f"Error creating document: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document: {str(e)}"
        )

@documents_router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Retrieve a document",
    description="Get a specific document by its ID"
)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
) -> DocumentResponse:
    """Retrieve a document by its ID."""
    try:
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with id {document_id} not found"
            )
        
        return DocumentResponse.model_validate(document)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document"
        )
        
@documents_router.post(
    "/{document_id}/question",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a question about a document",
    description="Submit a question for async processing and get immediate response with question ID"
)
async def submit_question(
    document_id: int,
    question_data: QuestionCreate,
    db: AsyncSession = Depends(get_db)
) -> QuestionResponse:
    """Submit a question about a specific document."""
    try:
        # Verify document exists
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with id {document_id} not found"
            )
        
        # Create question with pending status
        question = Question(
            document_id=document_id,
            question=question_data.question,
            status=QuestionStatus.PENDING.value
        )
        db.add(question)
        await db.commit()
        await db.refresh(question)
        
        # Start background processing
        try:
            from .database import async_session
            task = asyncio.create_task(
                process_question_async(question.id, question_data.question, async_session)
            )
            background_tasks[question.id] = task
            logger.info(f"Question {question.id} submitted for processing")
        except Exception as bg_error:
            logger.error(f"Failed to start background task: {str(bg_error)}")
            # Continue anyway - question was created successfully
        
        return QuestionResponse.model_validate(question)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating question: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create question: {str(e)}"
        )

@documents_router.get(
    "/{document_id}/questions",
    response_model=List[QuestionResponse],
    summary="Get all questions for a document",
    description="Retrieve all questions associated with a specific document"
)
async def get_document_questions(
    document_id: int,
    db: AsyncSession = Depends(get_db)
) -> List[QuestionResponse]:
    """Get all questions for a specific document."""
    try:
        # Verify document exists
        doc_result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = doc_result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with id {document_id} not found"
            )
        
        # Get questions
        questions_result = await db.execute(
            select(Question).where(Question.document_id == document_id).order_by(Question.created_at.desc())
        )
        questions = questions_result.scalars().all()
        
        return [QuestionResponse.model_validate(q) for q in questions]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting questions for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve questions"
        )

# Question endpoints
@questions_router.get(
    "/{question_id}",
    response_model=QuestionResponse,
    summary="Get question status and answer",
    description="Retrieve question details including processing status and answer (if available)"
)
async def get_question(
    question_id: int,
    db: AsyncSession = Depends(get_db)
) -> QuestionResponse:
    """Get question status and answer."""
    try:
        result = await db.execute(
            select(Question).where(Question.id == question_id)
        )
        question = result.scalar_one_or_none()
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with id {question_id} not found"
            )
        
        return QuestionResponse.model_validate(question)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting question {question_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve question"
        )

@questions_router.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a question",
    description="Delete a specific question (cancels processing if pending)"
)
async def delete_question(
    question_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a question."""
    try:
        result = await db.execute(
            select(Question).where(Question.id == question_id)
        )
        question = result.scalar_one_or_none()
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with id {question_id} not found"
            )
        
        # Cancel background task if it exists
        if question_id in background_tasks:
            background_tasks[question_id].cancel()
            del background_tasks[question_id]
            logger.info(f"Cancelled background task for question {question_id}")
        
        # Delete question
        await db.execute(delete(Question).where(Question.id == question_id))
        await db.commit()
        logger.info(f"Question {question_id} deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting question {question_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete question"
        )

# Health check endpoints
@health_router.get(
    "/",
    summary="Health check",
    description="Check if the service is running and database is accessible"
)
async def health_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """Health check endpoint."""
    try:
        # Test database connection with a simple query
        await db.execute(select(1))
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "healthy",
                "service": "document-qa-service",
                "version": "1.0.0",
                "database": "connected",
                "background_tasks": len(background_tasks)
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "document-qa-service",
                "error": "Database connection failed"
            }
        )

async def get_metrics(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """Get service metrics and statistics."""
    try:
        # Get document count
        doc_result = await db.execute(select(Document))
        doc_count = len(doc_result.scalars().all())
        
        # Get question count
        question_result = await db.execute(select(Question))
        question_count = len(question_result.scalars().all())
        
        metrics = {
            "total_documents": doc_count,
            "total_questions": question_count,
            "background_tasks_active": len(background_tasks)
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "metrics": metrics,
                "background_tasks_active": len(background_tasks),
                "background_task_ids": list(background_tasks.keys())
            }
        )
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )
@documents_router.post(
    "/upload-file",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload complex document files",
    description="Upload PDF, DOCX, or text files and extract content"
)
async def upload_complex_document(
    title: str = Form(..., description="Document title"),
    file: UploadFile = File(..., description="Document file (PDF, DOCX, TXT)"),
    db: AsyncSession = Depends(get_db)
) -> DocumentResponse:
    """Upload and process complex document files."""
    
    try:
        file_content = await file.read()
        extracted_text = ""
        
        # Handle different file types
        if file.filename.endswith('.pdf'):
            # PDF processing
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            for page in pdf_reader.pages:
                extracted_text += page.extract_text() + "\n"
                
        elif file.filename.endswith('.docx'):
            # Word document processing
            doc = docx.Document(io.BytesIO(file_content))
            for paragraph in doc.paragraphs:
                extracted_text += paragraph.text + "\n"
                
        elif file.filename.endswith('.txt'):
            # Plain text
            extracted_text = file_content.decode('utf-8')
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type. Use PDF, DOCX, or TXT files."
            )
        
        if not extracted_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract text from the uploaded file"
            )
        
        # Create document
        document = Document(
            title=title,
            content=extracted_text.strip()
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        logger.info(f"Complex document uploaded successfully: {document.id}")
        return DocumentResponse.model_validate(document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing complex document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )
  

# Export routers for main application
__all__ = ["documents_router", "questions_router", "health_router"]
