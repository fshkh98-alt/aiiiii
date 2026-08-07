from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
import logging

from app.models import ChatRequest, ChatResponse
from app.services.gemini_service import gemini_service
from app.services.cyber_filter import is_cyber_related, is_malicious_prompt
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

request_counts = {}

def check_rate_limit(client_ip: str, limit_type: str, max_requests: int = 10, window: int = 60):
    key = f"{client_ip}:{limit_type}"
    now = datetime.now().timestamp()

    if key not in request_counts:
        request_counts[key] = []

    request_counts[key] = [t for t in request_counts[key] if now - t < window]

    if len(request_counts[key]) >= max_requests:
        raise HTTPException(status_code=429, detail="Too many requests")

    request_counts[key].append(now)

@router.post("/api/chat")
async def chat_endpoint(request: Request, chat_request: ChatRequest):
    client_ip = request.client.host

    try:
        check_rate_limit(client_ip, "chat", max_requests=10, window=60)
    except HTTPException:
        raise

    if len(chat_request.message) > settings.MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail="Message too long")

    if is_malicious_prompt(chat_request.message):
        return ChatResponse(
            response="⚠️ تم رصد محاولة حقن أو طلب غير مصرح به.",
            timestamp=datetime.now().isoformat(),
            warning="security_alert"
        )

    if not is_cyber_related(chat_request.message):
        return ChatResponse(
            response="أنا مساعد متخصص في الأمن السيبراني. يرجى طرح أسئلة في هذا المجال فقط.",
            timestamp=datetime.now().isoformat()
        )

    try:
        response_text = await gemini_service.get_chat_response(
            chat_request.message, 
            chat_request.history
        )
        return ChatResponse(response=response_text, timestamp=datetime.now().isoformat())
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return ChatResponse(
            response=f"❌ خطأ: {str(e)}\n\nتأكد من:\n1. GEMINI_API_KEY صحيح\n2. API key فعال\n3. رصيد متاح",
            timestamp=datetime.now().isoformat(),
            warning="error"
        )

@router.get("/api/quiz")
async def quiz_endpoint(request: Request):
    client_ip = request.client.host

    try:
        check_rate_limit(client_ip, "quiz", max_requests=5, window=60)
    except HTTPException:
        raise

    try:
        question = await gemini_service.generate_quiz_question()
        return question
    except Exception as e:
        logger.error(f"Quiz error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/news")
async def news_endpoint(request: Request):
    client_ip = request.client.host

    try:
        check_rate_limit(client_ip, "news", max_requests=5, window=60)
    except HTTPException:
        raise

    try:
        news = await gemini_service.generate_cyber_news()
        return news
    except Exception as e:
        logger.error(f"News error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "model": settings.MODEL_NAME
    }
