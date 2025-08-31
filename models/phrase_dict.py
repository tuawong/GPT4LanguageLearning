from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import declarative_base
from .base import Base

class PhraseDict(Base):
    __tablename__ = "PhraseDict" 
    phrase_id = Column(String, nullable=False, unique=True, primary_key=True, index=True)
    line = Column(String, nullable=False)
    pinyin = Column(String, nullable=False)
    meaning = Column(String, nullable=False)
    response = Column(String, nullable=False)
    response_pinyin = Column(String, nullable=False)
    response_meaning = Column(String, nullable=False)
    complexity = Column(String, nullable=False)
    category = Column(String, nullable=False)
    tone = Column(String, nullable=False)
    added_date = Column(DateTime(timezone=True), server_default=func.now())


