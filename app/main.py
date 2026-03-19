from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.routers import render

load_dotenv()

app = FastAPI(
    title="VDX Render API",
    description="Motor de desenho técnico para aplicações de vidro",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(render.router)


@app.get("/health")
def health():
    return {"status": "ok", "versao": "1.0.0", "api": "VDX Render API"}
