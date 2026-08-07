import google.generativeai as genai
import json
import re
import logging
from app.config import settings
from app.prompts import SYSTEM_INSTRUCTION, QUIZ_PROMPT, NEWS_PROMPT
from app.models import Message

logger = logging.getLogger(__name__)

# Configure API
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    logger.info("Gemini API configured")
else:
    logger.error("GEMINI_API_KEY not set!")

class GeminiService:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY is not configured!")

        # Find working model automatically
        self.model_name = self._find_working_model()
        logger.info(f"Using model: {self.model_name}")

        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=SYSTEM_INSTRUCTION,
            safety_settings=settings.SAFETY_SETTINGS
        )

    def _find_working_model(self):
        """Auto-detect available Gemini model."""
        # Models to try (in order of preference)
        candidates = [
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash-8b",
            "gemini-1.5-flash-8b-latest",
            "gemini-1.5-pro",
            "gemini-1.5-pro-latest",
            "gemini-1.0-pro",
            "gemini-pro",
        ]

        # Try each model with a simple test
        for model_name in candidates:
            try:
                test_model = genai.GenerativeModel(model_name)
                # Quick test - just check if model exists
                response = test_model.generate_content(
                    "Say 'ok'",
                    generation_config={"max_output_tokens": 2}
                )
                if response and response.text:
                    logger.info(f"✅ Model works: {model_name}")
                    return model_name
            except Exception as e:
                error_str = str(e).lower()
                if "not found" in error_str or "404" in error_str:
                    logger.warning(f"❌ Model not found: {model_name}")
                elif "quota" in error_str or "429" in error_str:
                    logger.warning(f"⚠️ Quota exceeded: {model_name}")
                else:
                    logger.warning(f"⚠️ Model {model_name} error: {e}")
                continue

        # Try to list available models from API
        try:
            logger.info("Trying to list available models...")
            available_models = genai.list_models()
            gemini_models = []
            for m in available_models:
                name = m.name.replace("models/", "")
                if "gemini" in name.lower():
                    methods = getattr(m, 'supported_generation_methods', [])
                    if 'generateContent' in methods:
                        gemini_models.append(name)
                        logger.info(f"Found available model: {name}")

            if gemini_models:
                logger.info(f"Using first available: {gemini_models[0]}")
                return gemini_models[0]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")

        # Ultimate fallback
        logger.error("No working model found! Using gemini-pro as last resort.")
        return "gemini-pro"

    def _clean_json_response(self, text: str) -> str:
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        text = re.sub(r"^[^{\[]*", "", text)
        text = re.sub(r"[^}\]]*$", "", text)
        return text.strip()

    def _safe_json_loads(self, text: str, fallback=None):
        try:
            cleaned = self._clean_json_response(text)
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"JSON parse error: {e}")
            return fallback

    async def get_chat_response(self, message: str, history: list[Message]):
        try:
            gemini_history = []
            for msg in history:
                role = "user" if msg.role == "user" else "model"
                gemini_history.append({"role": role, "parts": [msg.content]})

            chat = self.model.start_chat(history=gemini_history)
            response = chat.send_message(message)

            if response and response.text:
                return response.text
            raise Exception("Empty response from Gemini")

        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise Exception(f"{str(e)}")

    async def generate_quiz_question(self):
        try:
            response = self.model.generate_content(QUIZ_PROMPT)
            if not response or not response.text:
                raise Exception("Empty response")

            result = self._safe_json_loads(response.text)
            if not result:
                raise Exception("Invalid JSON")
            return result

        except Exception as e:
            logger.error(f"Quiz error: {e}")
            return {
                "question": "ما هو الهدف الرئيسي من استخدام SIEM؟",
                "options": [
                    "تسريع أداء الشبكة",
                    "جمع وتحليل السجلات الأمنية في الوقت الفعلي",
                    "تصميم مواقع الويب",
                    "إدارة قواعد البيانات"
                ],
                "correct_answer": "جمع وتحليل السجلات الأمنية في الوقت الفعلي",
                "explanation": "SIEM يقوم بجمع وتحليل السجلات الأمنية من مصادر متعددة في الوقت الفعلي."
            }

    async def generate_cyber_news(self):
        try:
            response = self.model.generate_content(NEWS_PROMPT)
            if not response or not response.text:
                raise Exception("Empty response")

            result = self._safe_json_loads(response.text)
            if not result or not isinstance(result, list):
                raise Exception("Invalid JSON")
            return result

        except Exception as e:
            logger.error(f"News error: {e}")
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            return [
                {
                    "title": "اكتشاف ثغرة Zero-Day جديدة",
                    "summary": "أعلنت Microsoft عن وجود ثغرة أمنية خطيرة.",
                    "category": "Zero-Day",
                    "date": today
                },
                {
                    "title": "هجوم ransomware يستهدف القطاع الصحي",
                    "summary": "تعرضت مستشفيات لهجوم ransomware منسق.",
                    "category": "Ransomware",
                    "date": today
                },
                {
                    "title": "ثغرة في خدمات AWS",
                    "summary": "اكتشف باحثون ثغرة في إعدادات AWS.",
                    "category": "Cloud Security",
                    "date": today
                }
            ]

# Initialize
try:
    gemini_service = GeminiService()
except Exception as e:
    logger.error(f"Failed to initialize GeminiService: {e}")
    class DummyService:
        async def get_chat_response(self, *args):
            return "❌ Error: " + str(e)
        async def generate_quiz_question(self, *args):
            return {
                "question": "Error: " + str(e),
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "explanation": str(e)
            }
        async def generate_cyber_news(self, *args):
            return [{"title": "Error", "summary": str(e), "category": "Error", "date": "2024-01-01"}]
    gemini_service = DummyService()
