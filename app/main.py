# app/main.py
import json
import os
from dotenv import load_dotenv
from app.llm.survey_agent import get_survey
import uvicorn
from fastapi import FastAPI, Body
from fastapi import FastAPI, UploadFile, File
import base64
import httpx
import os

# Load .env file at startup
# Since your .env is at the root level (same level as the app directory),
# we need to adjust the path accordingly
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

app = FastAPI()
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


@app.get("/")
async def read_root():
    return {"message": "Hello World"}


@app.post("/survey")
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


async def get_survey_structure(image_description: str) -> dict:
    """Generate a structured survey based on image analysis"""

    survey_prompt = {
        "model": "gpt-4o",  # Updated to use GPT-4o
        "messages": [
            {
                "role": "system",
                "content": """Based on the image description, create a survey structure exactly matching this format. Respond with a JSON object:
                {
                    "personalInfo": {
                        "firstName": "text",
                        "lastName": "text",
                        "age": "number"
                    },
                    "employmentStatus": "select",
                    "employerDetails": {
                        "companyName": "text",
                        "position": "text",
                        "yearsEmployed": "number"
                    },
                    "educationLevel": "select",
                    "degrees": "multiple"
                }
                Make the survey relevant to what was seen in the image."""
            },
            {
                "role": "user",
                "content": f"Create a survey structure as a JSON object based on this image description: {image_description}"
            }
        ],
        "response_format": {"type": "json_object"}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            OPENAI_URL,
            json=survey_prompt,
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"}
        )
        result = response.json()
        return result['choices'][0]['message']['content']

@app.post("/analyze-image-survey")
async def analyze_image(file: UploadFile = File(...)):
    contents = await file.read()
    base64_image = base64.b64encode(contents).decode('utf-8')

    vision_payload = {
        "model": "gpt-4o",  # Updated to use GPT-4o
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text",
                     "text": "Analyze this image and describe what you see. Focus on the main subject and its context."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 300
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

        survey_structure = await get_survey_structure(image_description)

        return {
            "imageAnalysis": image_description,
            "surveyStructure": survey_structure
        }

@app.post("/analyze-text-survey")
async def analyze_text(input_data: dict = Body(...)):
    async with httpx.AsyncClient() as client:
        # Extract keywords
        keyword_prompt = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "Extract 5-10 most relevant and meaningful keywords from the given text. If the input is very short, expand it to related relevant concepts. Return only a comma-separated list of keywords."},
                {"role": "user", "content": f"Extract keywords from: {input_data['text']}"}
            ]
        }
        keyword_response = await client.post(OPENAI_URL, json=keyword_prompt, headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"})
        keywords = keyword_response.json()['choices'][0]['message']['content'].split(',')
        keywords = [keyword.strip() for keyword in keywords]

        # Generate survey structure
        survey_prompt = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": """Based on the provided keywords, create a survey structure as a JSON object exactly matching this format:
                {
                    "personalInfo": {
                        "firstName": "text",
                        "lastName": "text",
                        "age": "number"
                    },
                    "employmentStatus": "select",
                    "employerDetails": {
                        "companyName": "text",
                        "position": "text",
                        "yearsEmployed": "number"
                    },
                    "educationLevel": "select",
                    "degrees": "multiple"
                }
                Make the survey relevant to these keywords."""},
                {"role": "user", "content": f"Create a survey structure based on these keywords: {', '.join(keywords)}"}
            ],
            "response_format": {"type": "json_object"}
        }
        survey_response = await client.post(OPENAI_URL, json=survey_prompt, headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"})
        survey_structure = survey_response.json()['choices'][0]['message']['content']

    return {
        "originalText": input_data['text'],
        "extractedKeywords": keywords,
        "surveyStructure": json.loads(survey_structure)
    }

def start():
    """Launched with `poetry run start` at root level"""
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


def main():
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)


if __name__ == "__main__":
    main()
