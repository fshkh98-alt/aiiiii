from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
import logging
import traceback

from app.models import ChatRequest, ChatResponse
from app.services.gemini_service import gemini_service
from app.services.cyber_filter import is_cyber_related, is_malicious_prompt
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiting storage (simple in-memory)
request_counts = {}

def check_rate_limit(client_ip: str, limit_type: str, max_requests: int = 10, window: int = 60):
    """Simple rate limiting check."""
    key = f"{client_ip}:{limit_type}"
    now = datetime.now().timestamp()

    if key not in request_counts:
        request_counts[key] = []

    request_counts[key] = [t for t in request_counts[key] if now - t < window]

    if len(request_counts[key]) >= max_requests:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )

    request_counts[key].append(now)

@router.post("/api/chat")
async def chat_endpoint(request: Request, chat_request: ChatRequest):
    """Chat endpoint with cybersecurity filtering and rate limiting."""
    client_ip = request.client.host

    try:
        check_rate_limit(client_ip, "chat", max_requests=10, window=60)
    except HTTPException:
        raise

    if len(chat_request.message) > settings.MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Message too long. Maximum {settings.MAX_MESSAGE_LENGTH} characters allowed."
        )

    if is_malicious_prompt(chat_request.message):
        logger.warning(f"Malicious prompt detected from {client_ip}")
        return ChatResponse(
            response="⚠️ تم رصد محاولة حقن أو طلب غير مصرح به. هذا السؤال غير مسموح به لأسباب أمنية.",
            timestamp=datetime.now().isoformat(),
            warning="security_alert"
        )

    if not is_cyber_related(chat_request.message):
        return ChatResponse(
            response="أنا مساعد متخصص في الأمن السيبراني، لذلك لا أستطيع الإجابة عن الأسئلة خارج هذا المجال. يرجى طرح أسئلة تتعلق بالأمن السيبراني فقط.",
            timestamp=datetime.now().isoformat()
        )

    try:
        response_text = await gemini_service.get_chat_response(
            chat_request.message, 
            chat_request.history
        )
        return ChatResponse(
            response=response_text, 
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        error_msg = f"Chat error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        # Return actual error for debugging
        return ChatResponse(
            response=f"❌ ERROR: {str(e)}\n\nPlease check:\n1. GEMINI_API_KEY is set correctly\n2. API key has valid quota\n3. Model '{settings.MODEL_NAME}' is available",
            timestamp=datetime.now().isoformat(),
            warning="error"
        )

@router.get("/api/quiz")
async def quiz_endpoint(request: Request):
    """Quiz endpoint with rate limiting."""
    client_ip = request.client.host

    try:
        check_rate_limit(client_ip, "quiz", max_requests=5, window=60)
    except HTTPException:
        raise

    try:
        question = await gemini_service.generate_quiz_question()
        return question
    except Exception as e:
        error_msg = f"Quiz error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return {
            "question": "❌ خطأ في إنشاء السؤال: " + str(e),
            "options": ["تحقق من GEMINI_API_KEY", "تأكد من صلاحية المفتاح", "تأكد من وجود رصيد", "أعد المحاولة لاحقاً"],
            "correct_answer": "تحقق من GEMINI_API_KEY",
            "explanation": f"Error: {str(e)}"
        }

@router.get("/api/news")
async def news_endpoint(request: Request):
    """News endpoint with rate limiting."""
    client_ip = request.client.host

    try:
        check_rate_limit(client_ip, "news", max_requests=5, window=60)
    except HTTPException:
        raise

    try:
        news = await gemini_service.generate_cyber_news()
        return news
    except Exception as e:
        error_msg = f"News error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return [{
            "title": "❌ خطأ في جلب الأخبار",
            "summary": f"Error: {str(e)}. Please check GEMINI_API_KEY and quota.",
            "category": "Error",
            "date": datetime.now().strftime("%Y-%m-%d")
        }]

@router.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "model": settings.MODEL_NAME
    }
