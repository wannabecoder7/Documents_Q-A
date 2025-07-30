# app/services.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .models import Question, Document
from .schemas import QuestionCreate
from .enums import QuestionStatus

class QuestionService:
    @staticmethod
    async def create_question(db: AsyncSession, document_id: int, question_data: QuestionCreate):
        """Create a new question"""
        question = Question(
            document_id=document_id,
            question=question_data.question,
            status=QuestionStatus.PENDING.value
        )
        db.add(question)
        await db.commit()
        await db.refresh(question)
        return question

    @staticmethod
    async def update_question_answer(db: AsyncSession, question_id: int, answer: str):
        """Update question with answer"""
        result = await db.execute(
            select(Question).where(Question.id == question_id)
        )
        question = result.scalar_one_or_none()
        
        if question:
            question.answer = answer
            question.status = QuestionStatus.ANSWERED.value
            await db.commit()
            await db.refresh(question)
        
        return question
