from sqlalchemy import Column, Integer, String, DateTime, Float, func
from .base import Base


class APILatencyLog(Base):
    __tablename__ = "APILatencyLog"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    category = Column(String, nullable=False)          # e.g. 'translation', 'quiz_eval', 'phrase_gen', 'word_comparison'
    model = Column(String, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    reasoning_tokens = Column(Integer, nullable=True)
    num_items = Column(Integer, nullable=True)          # number of words/phrases in the request
    finish_reason = Column(String, nullable=True)       # response.status from the Responses API
    status = Column(String, nullable=False)             # 'success' or 'error'
    error_message = Column(String, nullable=True)
    estimated_cost_usd = Column(Float, nullable=True)
