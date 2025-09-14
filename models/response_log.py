from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import declarative_base
from .base import Base

class ResponseLog(Base):
    __tablename__ = "ResponseLog" 
    quiz_id = Column(String, nullable=False, unique=False, primary_key=True, index=False)
    prompt = Column(String, nullable=False)
    prompt_pinyin = Column(String, nullable=False)
    prompt_meaning = Column(String, nullable=False)
    response = Column(String, nullable=False)
    response_pinyin = Column(String, nullable=False)
    response_meaning = Column(String, nullable=False)
    correctness = Column(Integer, nullable=False)
    naturalness = Column(Integer, nullable=False)
    contextual_appropriateness = Column(Integer, nullable=False)
    comment = Column(String, nullable=False)
    complexity = Column(String, nullable=False)
    tone = Column(String, nullable=False)

