# app/main.py
import base64
import json
import logging
import os
import tempfile
import json
import os
import traceback
from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Union, Optional
from pydantic import BaseModel, Field
import traceback
from logging import getLogger
import json
import httpx
from fastapi import APIRouter, Body, Form
from pydantic import BaseModel

import httpx
from fastapi import Body, APIRouter
from fastapi import FastAPI, File
from fastapi import UploadFile, HTTPException
from openai import OpenAI, OpenAIError
from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Union
from pydantic import BaseModel, Field
import traceback
from logging import getLogger
import json

from app.llm.survey_agent import get_survey, generate_keywords, TextInput

logger = logging.getLogger(__name__)

app = FastAPI()
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
client = OpenAI()
MODEL = "gpt-4o"
survey_router = APIRouter()


class SurveyField(BaseModel):
    name: str
    label: str
    type: str
    required: bool
    options: Optional[List[str]] = None
    icon: Optional[str] = None
    multiline: Optional[bool] = None
    min: Optional[int] = None
    max: Optional[int] = None


class SurveySection(BaseModel):
    title: str
    fields: List[SurveyField]


class SurveyResponse(BaseModel):
    survey: List[SurveySection]


class KeywordsInput(BaseModel):
    keywords: str = Field(
        ...,
        description="Comma-separated keywords for survey generation",
        example='"office party", "celebration", "design"'
    )


@survey_router.post("/survey", response_model=SurveyResponse)
async def get_survey_call(keywords: KeywordsInput = Body(...)):
    """
    Endpoint to generate an event-themed survey structure based on provided keywords.

    Args:
        keywords (KeywordsInput): A Pydantic model containing keywords for survey generation.

    Returns:
        SurveyResponse: A Pydantic model containing the generated survey structure.

    Raises:
        HTTPException: If survey generation fails or invalid input is provided.
    """
    try:
        # Validate keywords
        if not keywords.keywords.strip():
            raise HTTPException(
                status_code=400,
                detail="Keywords string cannot be empty"
            )

        # Generate survey
        survey_json = get_survey(keywords.keywords)

        # Validate survey structure
        if not isinstance(survey_json, list):
            raise HTTPException(
                status_code=500,
                detail="Invalid survey structure generated"
            )

        # Create response using Pydantic model
        response = SurveyResponse(survey=survey_json)

        # Log successful generation
        logger.info(f"Successfully generated survey for keywords: {keywords.keywords}")

        return response

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON format: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in survey generation: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@survey_router.post("/analyze-image")
async def analyze_media(
        input_data: str = Form(...),
        file: UploadFile = File(...)
):
    """Analyze media (image/video) with associated text"""
    try:
        # Try to parse as JSON first
        text = ''
        try:
            text_input = TextInput.parse_raw(input_data)
            text = text_input.text
        except:
            # If JSON parsing fails, use the input string directly
            text = input_data

        # Read and encode the file
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode('utf-8')

        vision_payload = {
            "model": "gpt-4o",
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

        async with httpx.AsyncClient() as http_client:
            vision_response = await http_client.post(
                OPENAI_URL,
                json=vision_payload,
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                    "Content-Type": "application/json"
                }
            )
            vision_result = vision_response.json()
            image_description = vision_result['choices'][0]['message']['content']

            keyword_generation_text = f"TEXT: {text} IMAGE: {image_description}"
            keywords = await generate_keywords(keyword_generation_text)

            return {
                "imageAnalysis": image_description,
                "text": text,
                "extractedKeywords": keywords
            }
    except OpenAIError as oaie:
        traceback.print_exc()
        logger.error(f"OpenAI API error: {str(oaie)}")
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(oaie)}")
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@survey_router.post("/analyze-text")
async def analyze_text(input_data: TextInput):
    try:
        keywords = await generate_keywords(input_data.text)

        return {
            "originalText": input_data.text,
            "extractedKeywords": keywords
        }
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@survey_router.post("/analyze-voice")
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
        traceback.print_exc()
        logger.error(f"OpenAI API error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI API error: {str(e)}"
        )
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

# @survey_router.post("/generate-keywords")
# async def generate_keywords_endpoint(input_data: TextInput):
#     try:
#         keywords = await generate_keywords(input_data.text)
#         return {"keywords": keywords}
#     except Exception as e:
#         traceback.print_exc()
#         logger.error(f"Unexpected error: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"An unexpected error occurred: {str(e)}"
#         )

# @survey_router.post("/generate_simple_fields")
# async def generate_fields(input_data: TextInput):
#     try:
#         keywords = await generate_keywords(input_data.text)
#
#         async with httpx.AsyncClient() as http_client:
#             # Generate survey structure
#             survey_prompt = {
#                 "model": "gpt-4o",
#                 "messages": [
#                     {"role": "system", "content": """Based on the provided keywords, create a survey structure as a JSON object exactly matching this format:
#                     {
#                         "personalInfo": {
#                             "firstName": "text",
#                             "lastName": "text",
#                             "age": "number"
#                         },
#                         "employmentStatus": "select",
#                         "employerDetails": {
#                             "companyName": "text",
#                             "position": "text",
#                             "yearsEmployed": "number"
#                         },
#                         "educationLevel": "select",
#                         "degrees": "multiple"
#                     }
#                     Make the survey relevant to these keywords."""},
#                     {"role": "user",
#                      "content": f"Create a survey structure based on these keywords: {', '.join(keywords)}"}
#                 ],
#                 "response_format": {"type": "json_object"}
#             }
#             survey_response = await http_client.post(OPENAI_URL, json=survey_prompt,
#                                                      headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"})
#             survey_structure = survey_response.json()['choices'][0]['message']['content']
#
#         return {
#             "originalText": input_data.text,
#             "extractedKeywords": keywords,
#             "surveyStructure": json.loads(survey_structure)
#         }
#     except Exception as e:
#         traceback.print_exc()
#         logger.error(f"Unexpected error: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"An unexpected error occurred: {str(e)}"
#         )
