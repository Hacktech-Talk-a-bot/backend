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


def get_survey(input_fields_json):
    # Create a ChatOpenAI instance
    model = ChatOpenAI(model="gpt-4", temperature=0.0)

    examples = [
        {
            "input": '{"firstName": "text", "lastName": "text"}',
            "output": """[
  {
    "title": "Personal Information",
    "fields": [
      { "name": "firstName", "label": "First Name", "type": "text", "required": true },
      { "name": "lastName", "label": "Last Name", "type": "text", "required": true }
    ]
  }
]"""
        },
        {
            "input": '{"satisfaction": "slider", "mood": "icon"}',
            "output": """[
  {
    "title": "Feedback",
    "fields": [
      { "name": "satisfaction", "label": "Satisfaction", "type": "slider", "required": true },
      { "name": "mood", "label": "Mood", "type": "icon", "required": false, "icon": "faSmile" }
    ]
  }
]"""
        },
        {
            "input": '{"newsletter": "checkbox", "contactMethod": "select", "favoriteFruits": "multiple"}',
            "output": """[
  {
    "title": "Preferences",
    "fields": [
      { "name": "newsletter", "label": "Subscribe to Newsletter", "type": "checkbox", "required": false },
      { "name": "contactMethod", "label": "Preferred Contact Method", "type": "select", "required": true, "options": ["Email", "Phone"] },
      { "name": "favoriteFruits", "label": "Favorite Fruits", "type": "multiple", "required": false, "options": ["Apple", "Banana", "Cherry"] }
    ]
  }
]"""
        }
    ]

    # Create a prompt template for each example
    example_prompt = ChatPromptTemplate.from_messages([
        ("human", "Input JSON:\n{input}"),
        ("ai", "{output}")
    ])

    # Create the few-shot prompt template
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=examples
    )

    # Create the final prompt template
    final_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a helpful assistant that converts input JSON field definitions into structured survey JSON. Always output valid JSON without any additional text or explanations."),
        few_shot_prompt,
        ("human", "Input JSON:\n{input}")
    ])

    # Use the prompt with the model
    response = model.invoke(final_prompt.format_messages(input=input_fields_json))

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
            return {"error": "Invalid JSON output from the model.", "details": str(inner_e)}

    return survey_structure


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


class TextInput(BaseModel):
    text: str


async def generate_keywords(text: str) -> list:
    async with httpx.AsyncClient() as client:
        keyword_prompt = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system",
                 "content": "Extract 5-10 most relevant and meaningful keywords from the given text. If the input is very short, expand it to related relevant concepts. Return only a comma-separated list of keywords."},
                {"role": "user", "content": f"Extract keywords from: {text}"}
            ]
        }
        keyword_response = await client.post(OPENAI_URL, json=keyword_prompt,
                                             headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"})
        keywords = keyword_response.json()['choices'][0]['message']['content'].split(',')
        return [keyword.strip() for keyword in keywords]
