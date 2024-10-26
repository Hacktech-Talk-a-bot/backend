import traceback

from fastapi import FastAPI, Body
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
import json
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

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
client = OpenAI()


def get_survey(keywords_string: str):
    try:
        # Create a ChatOpenAI instance
        model = ChatOpenAI(model="gpt-4o", temperature=0.0)

        examples = [
            {
                "input": '"office party", "celebration", "festive"',
                "output": """[
            {
                "title": "Event Feedback",
                "fields": [
                    { 
                        "name": "eventSatisfaction", 
                        "label": "How would you rate the overall event?", 
                        "type": "slider", 
                        "required": true,
                        "min": 1,
                        "max": 5
                    },
                    {
                        "name": "atmosphere",
                        "label": "How would you describe the atmosphere?",
                        "type": "multiple",
                        "required": true,
                        "options": ["Energetic", "Festive", "Welcoming", "Professional", "Creative"]
                    }
                ]
            }
        ]"""
            },
            {
                "input": '"design", "theme", "creative"',
                "output": """[
            {
                "title": "Design & Theme Feedback",
                "fields": [
                    {
                        "name": "themeRating",
                        "label": "Rate the event's theme and decorations",
                        "type": "icon",
                        "required": true,
                        "icon": "faStar"
                    },
                    {
                        "name": "favoriteElements",
                        "label": "What were your favorite design elements?",
                        "type": "multiple",
                        "required": false,
                        "options": ["Colors", "Decorations", "Layout", "Lighting", "Music"]
                    }
                ]
            }
        ]"""
            },
            {
                "input": '"unity", "celebration", "promotion"',
                "output": """[
            {
                "title": "Team Experience",
                "fields": [
                    {
                        "name": "teamEngagement",
                        "label": "Did the event promote team unity?",
                        "type": "checkbox",
                        "required": true
                    },
                    {
                        "name": "futureSuggestions",
                        "label": "What would you like to see at future events?",
                        "type": "text",
                        "required": false,
                        "multiline": true
                    }
                ]
            }
        ]"""
            }
        ]

        # Create a prompt template for each example
        example_prompt = ChatPromptTemplate.from_messages([
            ("human", "Keywords:\n{input}"),
            ("ai", "{output}")
        ])

        # Create the few-shot prompt template
        few_shot_prompt = FewShotChatMessagePromptTemplate(
            example_prompt=example_prompt,
            examples=examples
        )

        # Create the final prompt template with specific instructions for event-themed surveys
        final_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful assistant that creates event feedback surveys. 
            Convert the provided keywords into a structured survey JSON focused on gathering feedback about 
            office events, parties, and creative celebrations. Include questions about atmosphere, 
            design elements, and overall experience. Always output valid JSON without any additional text."""),
            few_shot_prompt,
            ("human", "Keywords:\n{input}")
        ])

        # Use the prompt with the model
        response = model.invoke(final_prompt.format_messages(input=keywords_string))

        # Parse the response content to ensure it's valid JSON
        try:
            survey_structure = json.loads(response.content)
        except json.JSONDecodeError as e:
            # If the assistant's response is not valid JSON, attempt to extract the JSON part
            try:
                json_start = response.content.find('[')
                json_end = response.content.rfind(']')
                if json_start != -1 and json_end != -1:
                    survey_structure = json.loads(response.content[json_start:json_end + 1])
                else:
                    return {"error": "Invalid JSON output from the model.", "details": str(e)}
            except Exception as inner_e:
                traceback.print_exc()
                return {"error": "Invalid JSON output from the model.", "details": str(inner_e)}

        return survey_structure
    except Exception as e:
        traceback.print_exc()
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


async def get_survey_structure(image_description: str) -> dict:
    try:
        """Generate a structured survey based on image analysis"""

        survey_prompt = {
            "model": "gpt-4o",
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
    except Exception as e:
        traceback.print_exc()
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


class TextInput(BaseModel):
    text: str


async def generate_keywords(text: str) -> list:
    try:
        async with httpx.AsyncClient() as client:
            keyword_prompt = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system",
                     "content": "Extract 5-10 most relevant and meaningful keywords from the given text, which is structured with a combination of TEXT and IMAGE inputs. If the input is very short, expand it to related relevant concepts. Return only a comma-separated list of keywords. "},
                    {"role": "user", "content": f"Extract keywords from: {text}"}
                ]
            }
            keyword_response = await client.post(OPENAI_URL, json=keyword_prompt,
                                                 headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"})
            keywords = keyword_response.json()['choices'][0]['message']['content'].split(',')
            return [keyword.strip() for keyword in keywords]
    except Exception as e:
        traceback.print_exc()
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )
