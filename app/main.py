import logging
import os
import time

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

from app.api.endpoints import router
# from app.api.v1.endpoints import prototype  # Add sections import
from app.core.config import settings
from app.core.database import create_database
from app.llm.stream_router import stream_router
from app.llm.survey_router import survey_router

create_database()
# Load .env file at startup
# Since your .env is at the root level (same level as the app directory),
# we need to adjust the path accordingly
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

logger = logging.getLogger(__name__)



app = FastAPI()
app.include_router(survey_router, prefix=settings.API_V1_STR, tags=["survey"])
app.include_router(router, prefix=settings.API_V1_STR, tags=["forms"])
app.include_router(stream_router, prefix=settings.API_V1_STR, tags=["forms"])

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
client = OpenAI()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}s")
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    return {"message": "Hello World"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def main():
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)


if __name__ == "__main__":
    main()
