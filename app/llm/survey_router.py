# app/main.py
import base64
import json
import logging
import os
import tempfile
import traceback
from typing import AsyncGenerator
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from fastapi import FastAPI
from fastapi import File
from fastapi import Form
from fastapi import UploadFile
from fastapi.responses import StreamingResponse
from openai import OpenAI

from app.llm.models import SurveyResponse, KeywordsInput, SurveyField, SurveySection
from app.llm.survey_agent import get_survey, generate_keywords, TextInput, rewrite_section

logger = logging.getLogger(__name__)

app = FastAPI()
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
client = OpenAI()
MODEL = "gpt-4o"
survey_router = APIRouter()


@survey_router.post("/survey", response_model=SurveyResponse)
async def generate_survey(input_data: KeywordsInput):
    """
    Endpoint to generate a survey JSON structure based on keywords provided.

    Args:
        input_data (KeywordsInput): Input data containing a list of keywords for survey generation.

    Returns:
        dict: A dictionary containing the generated survey JSON.
    """
    try:
        # Validate keywords input
        keywords = input_data.keywords
        if not keywords:
            raise HTTPException(
                status_code=400,
                detail="Keywords list cannot be empty."
            )

        # Join the keywords list into a comma-separated string
        keywords_string = ", ".join(keywords)

        survey_json = get_survey(keywords_string)
        if not survey_json:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate survey structure."
            )

        # Validate the generated survey structure
        try:
            survey_sections = [SurveySection(**section) for section in survey_json]
        except Exception as e:
            logger.error(f"Invalid survey structure generated: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Generated survey structure is invalid."
            )

        return {"survey": survey_sections}

    except HTTPException as http_exc:
        # Return HTTP exceptions as they are
        raise http_exc
    except Exception as e:
        # Log unexpected errors and raise a generic HTTP exception
        traceback.print_exc()
        logger.error(f"Error generating survey: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@survey_router.post("/analyze-image")
async def analyze_media(
        input_data: Optional[str] = Form(None),
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
                            "text": "Analyze this image and provide a detailed description, focusing on the main objects in the image that are relevant for feedback. Identify key features or elements of these primary objects that could impact user experience, satisfaction, and overall impression. Consider topics like quality, aesthetic appeal, ambiance, and functionality depending on the image context, whether it's food presentation, decor, or location setup. Generate keywords that could be used to create a feedback form about the experience, ambiance, or satisfaction with this subject. These keywords should be versatile enough to inform questions related to user opinions, perceived quality, aesthetics, and suitability for the intended purpose, specifically focusing on the most prominent objects in the image."
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
    # allowed_extensions = ['.flac', '.m4a', '.mp3', '.mp4', '.mpeg', '.mpga', '.oga', '.ogg', '.wav', '.webm']
    file_ext = os.path.splitext(audio_file.filename)[1].lower()
    #
    # if file_ext not in allowed_extensions:
    #     raise HTTPException(
    #         status_code=400,
    #         detail=f"Unsupported file format. Supported formats: {allowed_extensions}"
    #     )

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


@survey_router.post("/regenerate-section")
async def regenerate_section(survey: SurveyResponse, survey_section: SurveyField) -> SurveyField:
    """
    Endpoint to regenerate a survey section.

    Args:
        survey: Complete survey response
        survey_section: Section to regenerate

    Returns:
        SurveyField: New regenerated survey field
    """
    try:
        new_field = rewrite_section(survey, survey_section)
        return new_field
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def generate_html_stream() -> AsyncGenerator[str, None]:
    """
    Generate streaming HTML content from GPT-4
    """
    try:
        async with httpx.AsyncClient() as client:
            prompt = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "system",
                        "content": """
                        You are an HTML generator that creates visually appealing, semantic HTML content. 
                        Follow these rules:
                        1. Generate valid HTML5 content
                        2. Use Bootstrap classes for styling
                        3. Include some interactive elements
                        4. Generate content gradually, section by section
                        5. Each section should be meaningful and complete
                        6. Do not include any ```html```, ```head```, or ```body``` tags - only the content.
                        7. Avoid using any COMMENTS. 
                        8. Generate only the content that would be rendered in the browser.
                        Do not include <html>, <head>, or <body> tags - only the content.
                        """
                    },
                    {
                        "role": "user",
                        "content": "Generate a visually appealing page about space exploration with sections for history, current missions, and future plans."
                    }
                ],
                "stream": True
            }

            async with client.stream(
                    "POST",
                    OPENAI_URL,
                    json=prompt,
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    }
            ) as response:
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Error from OpenAI API"
                    )

                # Process the streaming response
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        if line.strip() == "data: [DONE]":
                            break

                        try:
                            json_data = json.loads(line[6:])  # Remove "data: " prefix
                            content = json_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                # Yield the content chunk
                                yield content
                        except json.JSONDecodeError:
                            continue

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@survey_router.get("/generate_graphs")
async def generate_graphs():
    """
    Endpoint that returns a streaming response of HTML content
    """
    return StreamingResponse(
        generate_html_stream(),
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
