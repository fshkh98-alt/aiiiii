import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    # Use models/gemini-1.5-flash (with models/ prefix for v0.8.3)
    MODEL_NAME: str = os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash")
    ALLOWED_ORIGINS: list = ["*"]
    MAX_HISTORY_LENGTH: int = 50
    MAX_MESSAGE_LENGTH: int = 2000
    RATE_LIMIT_CHAT: str = "10/minute"
    RATE_LIMIT_QUIZ: str = "5/minute"
    RATE_LIMIT_NEWS: str = "5/minute"

    SAFETY_SETTINGS = [
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_LOW_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

settings = Settings()
