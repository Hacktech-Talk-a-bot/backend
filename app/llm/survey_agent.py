# app/main.py
import json
import os
import re
import traceback
from typing import List, Optional
from pydantic import BaseModel
import json

import httpx
from fastapi import HTTPException
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from openai import OpenAI
from pydantic import BaseModel

from app.llm.models import SurveyResponse, SurveyField

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
client = OpenAI()


def clean_and_parse_json(response_content: str) -> dict:
    """Clean JSON string of any extra tags/text and parse it."""
    try:
        # First attempt: direct JSON parse
        return json.loads(response_content)
    except json.JSONDecodeError:
        try:
            # Find content between first { and last }
            json_content = re.search(r'{.*}', response_content, re.DOTALL)
            if json_content:
                cleaned_json = json_content.group(0)
                # Remove any code block markers or other tags
                cleaned_json = re.sub(r'^```json\s*|^```\s*|\s*```$', '', cleaned_json.strip())
                return json.loads(cleaned_json)

            # If no {} found, try [] for arrays
            json_content = re.search(r'\[.*\]', response_content, re.DOTALL)
            if json_content:
                cleaned_json = json_content.group(0)
                cleaned_json = re.sub(r'^```json\s*|^```\s*|\s*```$', '', cleaned_json.strip())
                return json.loads(cleaned_json)

            raise ValueError("No JSON content found")

        except Exception as e:
            traceback.print_exc()
            return {"error": "Invalid JSON output from the model.", "details": str(e)}


def rewrite_section(survey_json: SurveyResponse, survey_field: SurveyField):
    """Return both entities as separate JSON strings."""

    survey_json = survey_json.model_dump_json(indent=2),
    field_json = survey_field.model_dump_json(indent=2)

    model = ChatOpenAI(model="gpt-4o", temperature=0.0)

    final_prompt = ChatPromptTemplate.from_messages([
        ("system",
         """
You are a helpful assistant that creates event feedback surveys. 


Your Task:
Your task is to rewrite the provided JSON subsection into another section that matches the topic, style, direction of the Form however, it does not have to be the exact same type or ask the same question.

Rules:
- The new section should be a valid JSON object.
- The new section should match the style, topic, direction of the form however, it does not have to be the exact same type or ask the same question.
- The new section should not be the same as the original section.
- The full form will be surrounded by a the <FORM></FORM> tags.
- The section will be surrounded by a the <FIELD></FIELD> tags.
- You will respond only with the required JSON object, absolutely no additional text.
"""),
        # few_shot_prompt,
        ("human", "<FORM>:{form}</FORM>, <FIELD>:{field}</FIELD>")
    ])

    response = model.invoke(final_prompt.format_messages(form=survey_json, field=field_json))

    try:
        survey_structure = clean_and_parse_json(response.content)
    except json.JSONDecodeError as e:
        # If the assistant's response is not valid JSON, attempt to extract the JSON part
        try:
            json_start = response.content.find('[')
            json_end = response.content.rfind(']')
            if json_start != -1 and json_end != -1:
                json_extracted = json.loads(response.content[json_start:json_end + 1])
                survey_structure = json_extracted
            else:
                return {"error": "Invalid JSON output from the model.", "details": str(e)}
        except Exception as inner_e:
            traceback.print_exc()
            return {"error": "Invalid JSON output from the model.", "details": str(inner_e)}
    return survey_structure


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
