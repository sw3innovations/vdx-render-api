from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
from app.routers import render, chat, feedback, preview
from app.core.constitution import init_db
from app.core.constitution_seed import seed as constitution_seed

load_dotenv()

app = FastAPI(
    title="VDX Render API",
    description="Motor de desenho técnico para aplicações de vidro",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vdx.sw3.tec.br",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(render.router)
app.include_router(chat.router)
app.include_router(feedback.router)
app.include_router(preview.router)


@app.on_event("startup")
def startup_event():
    init_db()
    constitution_seed()


@app.get("/health")
def health():
    return {"status": "ok", "versao": "1.0.0", "api": "VDX Render API"}
