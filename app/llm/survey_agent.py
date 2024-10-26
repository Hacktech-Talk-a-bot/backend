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
                "title": "OfficeEventFeedback",
                "fields": [
                    {
                    "name": "eventSatisfaction",
                    "label": "How would you rate the overall event?",
                    "type": "slider",
                    "required": true,
                    "min": 1,
                    "max": 10
                     },
                    {
                        "name": "atmosphere",
                        "label": "How would you describe the atmosphere?",
                        "type": "multiple",
                        "required": true,
                        "options": ["Energetic", "Festive", "Welcoming", "Professional", "Creative", "Relaxed", "Boring"]
                    },
                    {
                        "name": "favoriteActivity",
                        "label": "What was your favorite activity during the event?",
                        "type": "multiple",
                        "required": true,
                        "options": ["Dancing", "Games", "Karaoke", "Networking", "Photo Booth", "Other"]
                    },
                    {
                        "name": "entertainmentRating",
                        "label": "How would you rate the entertainment provided?",
                        "type": "slider",
                        "required": true,
                        "min": 1,
                        "max": 5
                    },
                    {
                        "name": "foodAndSnacks",
                        "label": "How satisfied were you with the food and snacks provided?",
                        "type": "slider",
                        "required": true,
                        "min": 1,
                        "max": 5
                    },
                    {
                        "name": "foodQuality",
                        "label": "How would you describe the quality of the food?",
                        "type": "multiple",
                        "required": true,
                        "options": ["Excellent", "Good", "Average", "Poor", "Very Poor"]
                    },
                    {
                        "name": "drinkSelection",
                        "label": "How was the selection of drinks?",
                        "type": "multiple",
                        "required": false,
                        "options": ["Great Variety", "Good", "Limited", "Poor"]
                    },
                    {
                        "name": "overallOrganization",
                        "label": "How would you rate the overall organization of the event?",
                        "type": "icon",
                        "required": true,
                        "icon": "faStar"
                    },
                    {
                        "name": "eventDuration",
                        "label": "Was the event duration appropriate?",
                        "type": "multiple",
                        "required": true,
                        "options": ["Too Short", "Just Right", "Too Long"]
                    },
                    {
                        "name": "networkingOpportunities",
                        "label": "How would you rate the networking opportunities at the event?",
                        "type": "slider",
                        "required": false,
                        "min": 1,
                        "max": 5
                    },
                    {
                        "name": "decorationFeedback",
                        "label": "Did you like the event decorations?",
                        "type": "checkbox",
                        "required": true
                    },
                    {
                        "name": "improvementSuggestions",
                        "label": "Any suggestions for making future office parties better?",
                        "type": "text",
                        "required": false,
                        "multiline": true
                    },
                    {
                        "name": "additionalComments",
                        "label": "Any other comments or feedback?",
                        "type": "text",
                        "required": false,
                        "multiline": true
                    }
                ]
            }
        ]"""
            },
            {
                "input": '"work environment", "employee satisfaction", "workplace culture"',
                "output": """[
            {
                "title": "Work Environment Feedback Survey",
                "fields": [
                    {
                        "name": "overallSatisfaction",
                        "label": "How satisfied are you with your current work environment?",
                        "type": "slider",
                        "required": true,
                        "min": 1,
                        "max": 10
                    },
                    {
                        "name": "workLifeBalance",
                        "label": "How would you rate your work-life balance?",
                        "type": "slider",
                        "required": true,
                        "min": 1,
                        "max": 5
                    },
                    {
                        "name": "physicalWorkspace",
                        "label": "How satisfied are you with the physical workspace (e.g., office, desk, amenities)?",
                        "type": "multiple",
                        "required": true,
                        "options": ["Very Satisfied", "Satisfied", "Neutral", "Dissatisfied", "Very Dissatisfied"]
                    },
                    {
                        "name": "teamCulture",
                        "label": "How would you describe the culture within your team?",
                        "type": "multiple",
                        "required": true,
                        "options": ["Collaborative", "Supportive", "Competitive", "Toxic", "Disconnected"]
                    },
                    {
                        "name": "managementFeedback",
                        "label": "How effective is your direct supervisor in supporting your needs?",
                        "type": "slider",
                        "required": true,
                        "min": 1,
                        "max": 5
                    },
                    {
                        "name": "communicationSatisfaction",
                        "label": "How would you rate communication within the company?",
                        "type": "multiple",
                        "required": true,
                        "options": ["Excellent", "Good", "Fair", "Poor"]
                    },
                    {
                        "name": "growthOpportunities",
                        "label": "Do you feel you have enough opportunities for professional growth?",
                        "type": "checkbox",
                        "required": true
                    },
                    {
                        "name": "trainingAndDevelopment",
                        "label": "How satisfied are you with the training and development programs offered?",
                        "type": "slider",
                        "required": false,
                        "min": 1,
                        "max": 5
                    },
                    {
                        "name": "workplaceSafety",
                        "label": "Do you feel the workplace environment is safe (e.g., health and safety, mental well-being)?",
                        "type": "multiple",
                        "required": true,
                        "options": ["Very Safe", "Safe", "Neutral", "Unsafe", "Very Unsafe"]
                    },
                    {
                        "name": "recognitionFeedback",
                        "label": "Do you feel your contributions are recognized and appreciated?",
                        "type": "icon",
                        "required": true,
                        "icon": "faStar"
                    },
                    {
                        "name": "stressFactors",
                        "label": "What are the main factors that contribute to your work-related stress?",
                        "type": "multiple",
                        "required": false,
                        "options": ["Workload", "Deadlines", "Lack of Support", "Management", "Coworkers", "Other"]
                    },
                    {
                        "name": "flexibilityPreference",
                        "label": "Would you like more flexibility in terms of work location or hours?",
                        "type": "checkbox",
                        "required": true
                    },
                    {
                        "name": "remoteWorkSupport",
                        "label": "How well does the company support remote work (if applicable)?",
                        "type": "slider",
                        "required": false,
                        "min": 1,
                        "max": 5
                    },
                    {
                        "name": "suggestionsForImprovement",
                        "label": "Do you have any suggestions for improving the work environment?",
                        "type": "text",
                        "required": false,
                        "multiline": true
                    },
                    {
                        "name": "additionalComments",
                        "label": "Any other comments or feedback you would like to share?",
                        "type": "text",
                        "required": false,
                        "multiline": true
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
            },
            {
                "input": '"workshop", "learning", "interactive"',
                "output": """[
            {
                "title": "Workshop Feedback",
                "fields": [
                    {
                        "name": "learningExperience",
                        "label": "How would you rate the overall learning experience?",
                        "type": "slider",
                        "required": true,
                        "min": 1,
                        "max": 10
                    },
                    {
                        "name": "contentRelevance",
                        "label": "How relevant was the workshop content to your needs?",
                        "type": "multiple",
                        "required": true,
                        "options": ["Extremely Relevant", "Very Relevant", "Somewhat Relevant", "Not Relevant"]
                    },
                    {
                        "name": "facilitatorEngagement",
                        "label": "How well did the facilitator engage the participants?",
                        "type": "icon",
                        "required": true,
                        "icon": "faStar"
                    },
                    {
                        "name": "interactiveElements",
                        "label": "How engaging were the interactive elements (e.g., group activities, discussions)?",
                        "type": "multiple",
                        "required": true,
                        "options": ["Excellent", "Good", "Average", "Poor", "None"]
                    },
                    {
                        "name": "paceOfWorkshop",
                        "label": "Was the pace of the workshop appropriate?",
                        "type": "multiple",
                        "required": true,
                        "options": ["Too Fast", "Just Right", "Too Slow"]
                    },
                    {
                        "name": "practicalApplication",
                        "label": "How confident are you in applying what you learned?",
                        "type": "slider",
                        "required": true,
                        "min": 1,
                        "max": 5
                    },
                    {
                        "name": "favoriteActivity",
                        "label": "Which activity did you find most beneficial?",
                        "type": "multiple",
                        "required": false,
                        "options": ["Hands-On Activity", "Discussion Groups", "Case Studies", "Q&A Session", "Lecture Segment"]
                    },
                    {
                        "name": "futureTopics",
                        "label": "What topics would you like to see covered in future workshops?",
                        "type": "text",
                        "required": false,
                        "multiline": true
                    },
                    {
                        "name": "suggestedImprovements",
                        "label": "Do you have any suggestions for improving future workshops?",
                        "type": "text",
                        "required": false,
                        "multiline": true
                    },
                    {
                        "name": "resourcesProvided",
                        "label": "How would you rate the quality of the materials and resources provided?",
                        "type": "slider",
                        "required": true,
                        "min": 1,
                        "max": 5
                    },
                    {
                        "name": "engagementTools",
                        "label": "How effective were the tools (e.g., slides, handouts, digital tools) used for engagement?",
                        "type": "multiple",
                        "required": true,
                        "options": ["Very Effective", "Effective", "Somewhat Effective", "Not Effective"]
                    },
                    {
                        "name": "networkingOpportunities",
                        "label": "Were there sufficient opportunities for networking with other participants?",
                        "type": "checkbox",
                        "required": false
                    },
                    {
                        "name": "futureParticipation",
                        "label": "Would you be interested in attending similar workshops in the future?",
                        "type": "checkbox",
                        "required": true
                    },
                    {
                        "name": "additionalComments",
                        "label": "Any other comments or feedback you would like to share?",
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
            ("system", """You are an AI survey generator specialized in creating structured feedback surveys for various employee-related topics.

            When provided with keywords describing an event, initiative, or topic, you will:

            - **Tailor Questions to the Topic**: Adapt survey questions based on the provided keywords, covering a range of potential scenarios, such as:
                - **Social Events** (e.g., office parties, team outings): Focus on satisfaction, atmosphere, activities, and social engagement.
                - **Leadership Changes** (e.g., new manager/director introductions): Focus on first impressions, communication style, team alignment, and leadership qualities.
                - **Professional Development** (e.g., workshops, training sessions): Include questions on content relevance, interactivity, facilitation, and practical application.
                - **Workplace Feedback** (e.g., work environment, culture surveys): Cover areas such as job satisfaction, team culture, workspace, and management support.

            - **Diverse Question Types**:
                - Use a combination of **sliders** (e.g., for ratings), **multiple-choice** (e.g., describing specific attributes), **checkboxes** (for simple yes/no questions), **icons** (e.g., star ratings), and **text fields** (for open-ended responses).
                - Include essential feedback areas such as **overall experience**, **specific highlights**, **areas for improvement**, and **additional comments** for each topic.

            - **Output Requirements**:
                - Generate valid JSON in a structured format, including `title` and `fields`.
                - Each field should specify `name`, `label`, `type`, and additional attributes as appropriate (e.g., `options` for multiple-choice).
                - Return strictly JSON output with no extraneous text or comments.

            Example Usage:
            - For keywords like "new manager, leadership, feedback," the survey should include questions on leadership style, team morale, communication, and onboarding experience.
            - For keywords like "office party, celebration, team bonding," the survey should focus on enjoyment, activities, and event organization.

            Remember to adapt each survey to align with the context and feedback goals of the provided keywords.
            """),

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
