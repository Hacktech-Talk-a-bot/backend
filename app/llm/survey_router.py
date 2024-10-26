# app/main.py
import base64
import json
import logging
import os
import tempfile
import traceback
from typing import List
from typing import Optional

from fastapi import APIRouter, HTTPException, Body
from fastapi import FastAPI, File
from fastapi import Form
from fastapi import UploadFile
from openai import OpenAI
from pydantic import BaseModel, Field

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
async def generate_survey(keywords: str = Body(..., embed=True)):
    """
    Endpoint to generate a survey JSON structure based on keywords provided.

    Args:
        keywords (str): A comma-separated string representing survey-related keywords.

    Returns:
        dict: A dictionary containing the generated survey JSON.
    """
    try:
        # Use the get_survey function with the provided keywords
        survey_json = get_survey(keywords)
        return {"survey": survey_json}
    except Exception as e:
        logger.error(f"Error generating survey: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@survey_router.post("/analyze-image")
async def analyze_media(
        input_data: str = Form(...),
        file: UploadFile = File(...)
):
    """Analyze media with associated text using GPT-4 vision capabilities."""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No file provided"
            )

        contents = await file.read()
        if not contents:
            raise HTTPException(
                status_code=400,
                detail="Empty file provided"
            )

        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File size exceeds 10MB limit"
            )

        # Validate file type
        content_type = file.content_type
        if not content_type or not content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only images are allowed."
            )

        # Try to parse as JSON first
        text = ''
        try:
            text_input = TextInput.parse_raw(input_data)
            text = text_input.text
        except:
            # If JSON parsing fails, use the input string directly
            text = input_data

        base64_image = base64.b64encode(contents).decode('utf-8')

        # Use GPT-4 for image analysis
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this image and describe what you see. Focus on the main subject in the image and its particular characteristics."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )

        image_description = response.choices[0].message.content
        keyword_generation_text = f"TEXT: {text} IMAGE: {image_description}"
        keywords = await generate_keywords(keyword_generation_text)

        return {
            "imageAnalysis": image_description,
            "text": text,
            "extractedKeywords": keywords
        }

    except Exception as e:
        logger.error(f"Error in analyze_media: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
    """Transcribe audio and analyze content using GPT-4o."""
    allowed_extensions = ['.flac', '.m4a', '.mp3', '.mp4', '.mpeg', '.mpga', '.oga', '.ogg', '.wav', '.webm']
    file_ext = os.path.splitext(audio_file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported formats: {allowed_extensions}"
        )

    try:
        content = await audio_file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Transcribe audio
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
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error in analyze_voice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
