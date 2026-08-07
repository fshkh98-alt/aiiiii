from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime

class Message(BaseModel):
    role: str = Field(..., pattern="^(user|model)$", description="Either 'user' or 'model'")
    content: str = Field(..., min_length=1, max_length=2000, description="The message content")

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    history: List[Message] = Field(default=[], max_length=50, description="Chat history")

    @validator('history')
    def validate_history_length(cls, v):
        if len(v) > 50:
            raise ValueError('Chat history cannot exceed 50 messages')
        return v

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    warning: Optional[str] = None

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: str

class NewsItem(BaseModel):
    title: str
    summary: str
    category: str
    date: str

class ErrorResponse(BaseModel):
    detail: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
