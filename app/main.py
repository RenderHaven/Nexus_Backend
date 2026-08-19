from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.router import api_router
from app.kafka.client import kafka_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await kafka_manager.start()
        print("Kafka producer started successfully")
    except Exception as e:
        print(f"Failed to start Kafka producer: {e}")
    yield
    await kafka_manager.stop()
    print("Kafka producer stopped")

app = FastAPI(
    title="Feed Builder API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/")
async def root():
    return {
        "message": "Feed Builder API"
    }  