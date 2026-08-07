from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
import logging

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

    # Remove old requests outside the window
    request_counts[key] = [t for t in request_counts[key] if now - t < window]

    if len(request_counts[key]) >= max_requests:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )

    request_counts[key].append(now)

@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: Request, chat_request: ChatRequest):
    """Chat endpoint with cybersecurity filtering and rate limiting."""
    client_ip = request.client.host

    try:
        check_rate_limit(client_ip, "chat", max_requests=10, window=60)
    except HTTPException:
        raise

    # Validate message length
    if len(chat_request.message) > settings.MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Message too long. Maximum {settings.MAX_MESSAGE_LENGTH} characters allowed."
        )

    # Check for prompt injection attempts
    if is_malicious_prompt(chat_request.message):
        logger.warning(f"Malicious prompt detected from {client_ip}")
        return ChatResponse(
            response="⚠️ تم رصد محاولة حقن أو طلب غير مصرح به. هذا السؤال غير مسموح به لأسباب أمنية.",
            timestamp=datetime.now().isoformat(),
            warning="security_alert"
        )

    # Check if message is cybersecurity related
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
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="حدث خطأ في معالجة طلبك. يرجى المحاولة مرة أخرى."
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
        logger.error(f"Quiz error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="فشل في إنشاء سؤال الاختبار. يرجى المحاولة لاحقاً."
        )

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
        logger.error(f"News error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="فشل في جلب الأخبار. يرجى المحاولة لاحقاً."
        )

@router.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
