from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import declarative_base
from .base import Base

class QuizAgg(Base):
    __tablename__ = "QuizAgg" 
    word_id = Column(String, ForeignKey("WordDict.word_id", ondelete="CASCADE"), primary_key=True)
    num_quiz_attempt = Column(Integer, default=0)
    num_correct = Column(Integer, default=0)
    num_wrong = Column(Integer, default=0)
    last_quiz = Column(DateTime(timezone=True), nullable=True)
