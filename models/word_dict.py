from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import declarative_base
from .base import Base

class WordDict(Base):
    __tablename__ = "WordDict"  # this is the table name in the DB

    word_id = Column(String, nullable=False, unique=True, primary_key=True, index=True)
    word = Column(String, nullable=False)
    pinyin = Column(String, nullable=False)
    pinyin_simplified = Column(String, nullable=False)
    type = Column(String, nullable=False)
    word_category = Column(String, nullable=False)
    word_rarity = Column(String, nullable=False)
    meaning = Column(String, nullable=False)
    sentence = Column(String, nullable=False)
    sentence_pinyin = Column(String, nullable=False)
    sentence_meaning = Column(String, nullable=False)
    added_date = Column(DateTime(timezone=True), server_default=func.now())
    #It's better to track quiz stats in a separate table to allow for multiple quiz attempts over time
    #We can display quiz stats in the app by querying the quiz attempts table and doing groupby 
    #num_quiz_attempt = Column(Integer, default=0)
    #num_correct = Column(Integer, default=0)
    #num_wrong = Column(Integer, default=0)
    #last_quiz = Column(DateTime(timezone=True), nullable=True)