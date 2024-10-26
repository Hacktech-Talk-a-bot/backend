# app/main.py
import json
import os
import tempfile

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


@app.get("/")
async def read_root():
    return {"message": "Hello World"}


# def start():
#     """Launched with `poetry run start` at root level"""
#     uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
#
#
# def main():
#     uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

def main():
    # Get the ngrok token from environment variable
    ngrok_token = os.environ.get("NGROK_AUTH_TOKEN")
    if not ngrok_token:
        raise ValueError("NGROK_AUTH_TOKEN environment variable is not set")

    # Set up ngrok
    ngrok.set_auth_token(ngrok_token)

    # Your custom domain
    custom_domain = "magnetic-wombat-centrally.ngrok-free.app"

    try:
        # Open a ngrok tunnel to the HTTP server with your custom domain
        listener = ngrok.connect(8080, domain=custom_domain)
        public_url = listener.public_url
        print(f"ngrok tunnel established: {public_url}")

        # Test the connection
        response = requests.get(f"{public_url}")
        if response.status_code == 200:
            print("Successfully connected to the ngrok tunnel!")
            print(f"Response from server: {response.json()}")
        else:
            print(f"Failed to connect to the ngrok tunnel. Status code: {response.status_code}")

        # Start the FastAPI app
        uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

    except ngrok.PyngrokError as e:
        print(f"ngrok error: {str(e)}")
    except requests.RequestException as e:
        print(f"Error testing the connection: {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")


if __name__ == "__main__":
    main()
