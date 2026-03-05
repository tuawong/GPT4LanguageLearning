from sqlalchemy import Column, Integer, String, DateTime, func
from .base import Base


class WordComparison(Base):
    __tablename__ = "WordComparison"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word1 = Column(String, nullable=False)
    word1_pinyin = Column(String, nullable=True)
    word2 = Column(String, nullable=False)
    word2_pinyin = Column(String, nullable=True)
    meaning = Column(String, nullable=True)
    part_of_speech_1 = Column(String, nullable=True)
    part_of_speech_2 = Column(String, nullable=True)
    word1_nuance = Column(String, nullable=True)
    word2_nuance = Column(String, nullable=True)
    word1_tone = Column(String, nullable=True)
    word2_tone = Column(String, nullable=True)
    word1_example = Column(String, nullable=True)
    word1_example_pinyin = Column(String, nullable=True)
    word1_example_meaning = Column(String, nullable=True)
    word2_example = Column(String, nullable=True)
    word2_example_pinyin = Column(String, nullable=True)
    word2_example_meaning = Column(String, nullable=True)
    added_date = Column(DateTime(timezone=True), server_default=func.now())
