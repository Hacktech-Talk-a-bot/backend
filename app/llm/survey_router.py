# app/main.py
import base64
import json
import logging
import os
import tempfile
import json
import os
import httpx
from fastapi import APIRouter, Body
from pydantic import BaseModel

import httpx
from fastapi import Body, APIRouter
from fastapi import FastAPI, File
from fastapi import UploadFile, HTTPException
from openai import OpenAI, OpenAIError

from app.llm.survey_agent import get_survey, generate_keywords, TextInput

logger = logging.getLogger(__name__)

app = FastAPI()
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
client = OpenAI()

survey_router = APIRouter()


@survey_router.post("/survey")
async def get_survey_call(input_json: str = Body(..., embed=True)):
    """
    Endpoint to generate a survey JSON structure based on input field definitions.

    Args:
        input_json (str): A JSON string representing input field definitions.

    Returns:
        dict: A dictionary containing the generated survey JSON.
    """
    survey_json = get_survey(input_json)
    return {"survey": survey_json}


@survey_router.post("/generate-keywords")
async def generate_keywords_endpoint(input_data: TextInput):
    keywords = await generate_keywords(input_data.text)
    return {"keywords": keywords}


@survey_router.post("/analyze-image-survey")
async def analyze_image(file: UploadFile = File(...)):
    contents = await file.read()
    base64_image = base64.b64encode(contents).decode('utf-8')
    try:
        vision_payload = {
            "model": "gpt-4o",  # Updated to use GPT-4 Vision
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text",
                         "text": "Analyze this image and describe what you see. Focus on the main subject in the image and its particular characteristics."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 500
        }

        async with httpx.AsyncClient() as client:
            vision_response = await client.post(
                OPENAI_URL,
                json=vision_payload,
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                    "Content-Type": "application/json"
                }
            )
            vision_result = vision_response.json()
            image_description = vision_result['choices'][0]['message']['content']

            # Extract keywords using the same function as analyze_text
            keywords = await generate_keywords(image_description)

            return {
                "imageAnalysis": image_description,
                "extractedKeywords": keywords
            }
    except OpenAIError as oaie:
        logger.error(f"OpenAI API error: {str(oaie)}")
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(oaie)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@survey_router.post("/analyze-text")
async def analyze_text(input_data: TextInput):
    keywords = await generate_keywords(input_data.text)

    return {
        "originalText": input_data.text,
        "extractedKeywords": keywords
    }


#
# @survey_router.post("/analyze-text-survey")
# async def analyze_text(input_data: TextInput):
#     keywords = await generate_keywords(input_data.text)
#
#     async with httpx.AsyncClient() as client:
#         # Generate survey structure
#         survey_prompt = {
#             "model": "gpt-4o",
#             "messages": [
#                 {"role": "system", "content": """Based on the provided keywords, create a survey structure as a JSON object exactly matching this format:
#                 {
#                     "personalInfo": {
#                         "firstName": "text",
#                         "lastName": "text",
#                         "age": "number"
#                     },
#                     "employmentStatus": "select",
#                     "employerDetails": {
#                         "companyName": "text",
#                         "position": "text",
#                         "yearsEmployed": "number"
#                     },
#                     "educationLevel": "select",
#                     "degrees": "multiple"
#                 }
#                 Make the survey relevant to these keywords."""},
#                 {"role": "user", "content": f"Create a survey structure based on these keywords: {', '.join(keywords)}"}
#             ],
#             "response_format": {"type": "json_object"}
#         }
#         survey_response = await client.post(OPENAI_URL, json=survey_prompt,
#                                             headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"})
#         survey_structure = survey_response.json()['choices'][0]['message']['content']
#
#     return {
#         "originalText": input_data.text,
#         "extractedKeywords": keywords,
#         "surveyStructure": json.loads(survey_structure)
#     }


@survey_router.post("/analyze-voice-survey")
async def analyze_voice_survey(audio_file: UploadFile = File(...)):
    allowed_extensions = ['.flac', '.m4a', '.mp3', '.mp4', '.mpeg', '.mpga', '.oga', '.ogg', '.wav', '.webm']
    file_ext = os.path.splitext(audio_file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported formats: {allowed_extensions}"
        )

    try:
        # Read file content
        content = await audio_file.read()

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Get transcription
            with open(temp_file_path, "rb") as audio:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    response_format="text"
                )

            keywords = await generate_keywords(transcript)

            return {
                "originalText": {"transcript": transcript},
                "extractedKeywords": keywords
            }

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except OpenAIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI API error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )
