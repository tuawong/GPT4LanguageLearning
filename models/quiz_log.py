from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import declarative_base
from .base import Base

class QuizLog(Base):
    __tablename__ = "QuizLog" 
    quiz_id = Column(String, nullable=False, unique=False, primary_key=True, index=False)
    word_id = Column(String, nullable=False)
    word = Column(String, nullable=False)
    sentence = Column(String, nullable=False)
    sentence_pinyin = Column(String, nullable=False)
    pinyin_answer = Column(String, nullable=False)
    pinyin_correct = Column(String, nullable=False)
    pinyin_correction = Column(String, nullable=False)
    meaning = Column(String, nullable=False)
    meaning_correct = Column(String, nullable=False)
    meaning_correction = Column(String, nullable=False)
    last_quiz = Column(DateTime(timezone=True), server_default=func.now())
