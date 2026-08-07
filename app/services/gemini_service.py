import google.generativeai as genai
import json
import re
import logging
from app.config import settings
from app.prompts import SYSTEM_INSTRUCTION, QUIZ_PROMPT, NEWS_PROMPT
from app.models import Message

logger = logging.getLogger(__name__)

# Available models for fallback
FALLBACK_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest", 
    "gemini-1.5-pro",
    "gemini-1.5-pro-latest",
    "gemini-pro",
    "gemini-1.0-pro",
]

class GeminiService:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise Exception("GEMINI_API_KEY is not configured!")

        genai.configure(api_key=settings.GEMINI_API_KEY)

        # Try to find working model
        self.model_name = self._find_working_model()
        logger.info(f"Selected model: {self.model_name}")

        self.model = genai.GenerativeModel(
            self.model_name,
            system_instruction=SYSTEM_INSTRUCTION,
            safety_settings=settings.SAFETY_SETTINGS
        )

    def _find_working_model(self):
        """Test each model until one works."""
        for model_name in FALLBACK_MODELS:
            try:
                test_model = genai.GenerativeModel(model_name)
                # Quick test
                response = test_model.generate_content("Hi", generation_config={"max_output_tokens": 1})
                if response and response.text:
                    logger.info(f"Model {model_name} works!")
                    return model_name
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}")
                continue

        # If none work, try listing available models
        try:
            available = genai.list_models()
            logger.info(f"Available models: {[m.name for m in available]}")

            # Find any gemini model
            for m in available:
                if "gemini" in m.name.lower() and "generateContent" in m.supported_generation_methods:
                    name = m.name.replace("models/", "")
                    logger.info(f"Using available model: {name}")
                    return name
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
            gemini_history = [
                {"role": msg.role if msg.role == "user" else "model", "parts": [msg.content]}
                for msg in history
            ]

            chat = self.model.start_chat(history=gemini_history)
            response = chat.send_message(message)

            if not response or not response.text:
                raise Exception("Empty response")

            return response.text

        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise Exception(f"{e}")

    async def generate_quiz_question(self):
        try:
            temp_model = genai.GenerativeModel(self.model_name)
            response = temp_model.generate_content(QUIZ_PROMPT)

            if not response or not response.text:
                raise Exception("Empty response")

            result = self._safe_json_loads(response.text)
            if not result:
                raise Exception("Invalid JSON response")

            return result

        except Exception as e:
            logger.error(f"Quiz error: {e}")
            raise Exception(f"{e}")

    async def generate_cyber_news(self):
        try:
            temp_model = genai.GenerativeModel(self.model_name)
            response = temp_model.generate_content(NEWS_PROMPT)

            if not response or not response.text:
                raise Exception("Empty response")

            result = self._safe_json_loads(response.text)
            if not result or not isinstance(result, list):
                raise Exception("Invalid JSON response")

            return result

        except Exception as e:
            logger.error(f"News error: {e}")
            raise Exception(f"{e}")

# Initialize
try:
    gemini_service = GeminiService()
except Exception as e:
    logger.error(f"Failed to initialize GeminiService: {e}")
    # Create dummy service
    class DummyService:
        async def get_chat_response(self, *args):
            return "❌ Service not available. Error: " + str(e)
        async def generate_quiz_question(self, *args):
            raise Exception(str(e))
        async def generate_cyber_news(self, *args):
            raise Exception(str(e))
    gemini_service = DummyService()
