from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Ensure the static directory exists so the app can start even without assets yet.
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Web Service Hub",
    description="다양한 웹 서비스를 관리하는 중앙 허브",
    version="1.0.0",
)

# Mount static files relative to this module for predictable paths.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Configure Jinja templates directory.
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """메인 홈페이지"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "message": "Web Service Hub is running!"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
