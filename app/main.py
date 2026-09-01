from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.errors import register_error_handlers
from app.api.router import api_router

app = FastAPI(
    title="Feed Builder API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(api_router)

@app.get("/")
async def root():
    return {
        "message": "Feed Builder API"
    }  