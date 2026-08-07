import os
import logging
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router as api_router
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CyberSentinel AI",
    description="Intelligent Cybersecurity Learning & Analysis Assistant",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENV") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENV") != "production" else None,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "حدث خطأ غير متوقع. يرجى المحاولة لاحقاً.",
            "timestamp": datetime.now().isoformat()
        }
    )

# CORS - allow all in dev, restrict in production
origins = ["*"]
if os.getenv("ENV") == "production":
    allowed = os.getenv("ALLOWED_ORIGINS", "")
    if allowed:
        origins = allowed.split(",")
    logger.info(f"CORS origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Static files - IMPORTANT: mount BEFORE routes
base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")
template_dir = os.path.join(base_dir, "templates")

logger.info(f"Static dir: {static_dir}")
logger.info(f"Template dir: {template_dir}")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=template_dir)

# API routes
app.include_router(api_router)

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/test")
async def test_page(request: Request):
    return templates.TemplateResponse("test.html", {"request": request})

@app.get("/favicon.ico")
async def favicon():
    return {"message": "No favicon"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
