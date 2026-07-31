from fastapi import FastAPI

from app.api.router import api_router


app = FastAPI(
    title="Feed Builder API",
    version="1.0.0",
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "message": "Feed Builder API is running"
    }