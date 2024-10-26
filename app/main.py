# app/main.py
import json
import os
import tempfile
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
import time
import requests
from dotenv import load_dotenv
from app.llm.survey_agent import get_survey
import uvicorn
from fastapi import FastAPI, Body
from fastapi import FastAPI, UploadFile, File
import base64
import httpx
import os
from pyngrok import ngrok
import openai
from fastapi import UploadFile, HTTPException
import logging
from openai import OpenAI, OpenAIError
from fastapi import UploadFile, HTTPException
import logging

from app.llm.survey_router import survey_router

# Load .env file at startup
# Since your .env is at the root level (same level as the app directory),
# we need to adjust the path accordingly
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(survey_router, prefix="/api", tags=["survey"])
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
client = OpenAI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}s")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
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

# def start():
#     """Launched with `poetry run start` at root level"""
#     uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
#
#
def main():
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

# def main():
#     ngrok_token = os.environ.get("NGROK_AUTH_TOKEN")
#     if not ngrok_token:
#         logger.error("NGROK_AUTH_TOKEN environment variable is not set")
#         raise ValueError("NGROK_AUTH_TOKEN environment variable is not set")
#
#     custom_domain = "magnetic-wombat-centrally.ngrok-free.app"
#
#     try:
#         listener = ngrok.connect(8080, domain=custom_domain)
#         public_url = listener.public_url
#         logger.info(f"ngrok tunnel established: {public_url}")
#
#         response = requests.get(f"{public_url}")
#         if response.status_code == 200:
#             logger.info("Successfully connected to the ngrok tunnel!")
#             logger.info(f"Response from server: {response.json()}")
#         else:
#             logger.error(f"Failed to connect to the ngrok tunnel. Status code: {response.status_code}")
#
#         uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
#
#     except ngrok.PyngrokError as e:
#         logger.error(f"ngrok error: {str(e)}")
#     except requests.RequestException as e:
#         logger.error(f"Error testing the connection: {str(e)}")
#     except Exception as e:
#         logger.error(f"An unexpected error occurred: {str(e)}")


if __name__ == "__main__":
    main()
