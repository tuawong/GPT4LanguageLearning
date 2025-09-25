from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import declarative_base
from .base import Base

class TranslationLog(Base):
    __tablename__ = "TranslationLog" 
    quiz_id = Column(String, nullable=False, unique=False, primary_key=True, index=False)
    prompt = Column(String, nullable=False)
    prompt_pinyin = Column(String, nullable=False)
    user_translation = Column(String, nullable=False)
    correct_translation = Column(String, nullable=False)
    correctness = Column(Integer, nullable=False)
    tone_correctness = Column(Integer, nullable=False)
    comment = Column(String, nullable=False)
    complexity = Column(String, nullable=False)
    tone = Column(String, nullable=False)
