import json
import logging
import os
from typing import AsyncGenerator, Optional
from pydantic import BaseModel

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

logger = logging.getLogger(__name__)
stream_router = APIRouter()


class SurveyRequest(BaseModel):
    survey_type: str
    custom_prompt: Optional[str] = None


# Predefined messages and system prompts
SYSTEM_MESSAGE = """You are an expert frontend developer specializing in data visualization. Your task is to create beautiful and insightful visualizations using HTML, CSS, and Bootstrap classes based on survey results.

First, examine the following survey structure and answers:

Your goal is to generate functional HTML, CSS, and Bootstrap code that effectively visualizes the survey results. Follow these steps:

1. Analyze the survey structure:
   - Identify the types of questions (multiple choice, open-ended, etc.)
   - Determine the corresponding data types for each question

2. Analyze the survey answers:
   - Review the responses for each question
   - Note any patterns or significant findings

3. Determine the most appropriate types of visualizations (e.g., charts, graphs, tables) for each question type:
   - List potential visualization options for each question
   - Justify your choice for each visualization

4. Plan the overall layout and design of the visualization dashboard

5. Create the HTML structure for the visualizations.

6. Write CSS styles to enhance the appearance of the visualizations.

7. Apply Bootstrap classes for responsive design and additional styling.

8. Combine all elements into a single HTML file with inline styles.

Important guidelines:
- Generate only functional HTML, CSS, and Bootstrap classes.
- Do not include any explanations or additional components outside of the HTML structure.
- Use a minimalist design and reuse created classes when possible.
- Aggregate the results effectively to provide meaningful insights.
- Ensure all visualizations are contained within a single <div> element.
- Avoid using any other javascript libraries when generating the code.
- VERY IMPORTANT:  Avoid using recharts and @/components/ui/card!!!!! AVOID


Visual guidelines:
- Use a minimalist design and reuse created classes when possible.
- Structure the HTML and CSS to structurally split the screen in 2 columns vertically. 
- Each of the 2 columns should have a maximum width of 100% while being held inside a div that a width of 100% as well.
- Use a responsive design approach to ensure the layout adapts to different screen sizes.
- Use a consistent color scheme and typography throughout the design.

After your planning, provide the complete HTML code, including all necessary CSS and Bootstrap classes, wrapped in <visualization_code> tags.

Remember, the success of your visualization will be judged on both its technical correctness and its ability to provide meaningful insights into the survey data."""


async def stream_anthropic_response(survey_type: str, custom_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
    # Construct the appropriate message based on survey type
    user_message = """
    <survey_structure>
[
    {
      "title": "Reward and Recognition Feedback Survey",
      "fields": [
        {
          "name": "programAwareness",
          "label": "How aware are you of the current reward and recognition programs in place?",
          "type": "multiple",
          "required": true,
          "options": [
            "Very Aware",
            "Somewhat Aware",
            "Not Very Aware",
            "Not Aware at All"
          ],
          "icon": null,
          "multiline": null,
          "min": null,
          "max": null
        },
        {
          "name": "programSatisfaction",
          "label": "How satisfied are you with the current reward and recognition programs?",
          "type": "slider",
          "required": true,
          "options": null,
          "icon": null,
          "multiline": null,
          "min": 1,
          "max": 10
        },
        {
          "name": "fairness",
          "label": "Do you feel the reward and recognition process is fair?",
          "type": "multiple",
          "required": true,
          "options": [
            "Very Fair",
            "Fair",
            "Neutral",
            "Unfair",
            "Very Unfair"
          ],
          "icon": null,
          "multiline": null,
          "min": null,
          "max": null
        },
        {
          "name": "motivationImpact",
          "label": "How much do the reward and recognition programs motivate you to perform better?",
          "type": "slider",
          "required": true,
          "options": null,
          "icon": null,
          "multiline": null,
          "min": 1,
          "max": 5
        },
        {
          "name": "recognitionFrequency",
          "label": "How often do you receive recognition for your work?",
          "type": "multiple",
          "required": true,
          "options": [
            "Very Often",
            "Often",
            "Sometimes",
            "Rarely",
            "Never"
          ],
          "icon": null,
          "multiline": null,
          "min": null,
          "max": null
        },
        {
          "name": "preferredRecognitionType",
          "label": "What type of recognition do you value the most?",
          "type": "multiple",
          "required": true,
          "options": [
            "Public Acknowledgment",
            "Private Praise",
            "Monetary Rewards",
            "Career Advancement Opportunities",
            "Other"
          ],
          "icon": null,
          "multiline": null,
          "min": null,
          "max": null
        },
        {
          "name": "programEffectiveness",
          "label": "How effective do you think the current programs are in recognizing employee achievements?",
          "type": "icon",
          "required": true,
          "options": null,
          "icon": "faStar",
          "multiline": null,
          "min": null,
          "max": null
        },
        {
          "name": "improvementSuggestions",
          "label": "What improvements would you suggest for the reward and recognition programs?",
          "type": "text",
          "required": false,
          "options": null,
          "icon": null,
          "multiline": true,
          "min": null,
          "max": null
        },
        {
          "name": "peerRecognition",
          "label": "Do you feel encouraged to recognize your peers?",
          "type": "checkbox",
          "required": true,
          "options": null,
          "icon": null,
          "multiline": null,
          "min": null,
          "max": null
        },
        {
          "name": "managerRecognition",
          "label": "How often does your manager recognize your contributions?",
          "type": "multiple",
          "required": true,
          "options": [
            "Very Often",
            "Often",
            "Sometimes",
            "Rarely",
            "Never"
          ],
          "icon": null,
          "multiline": null,
          "min": null,
          "max": null
        },
        {
          "name": "programClarity",
          "label": "Is the criteria for receiving rewards and recognition clear to you?",
          "type": "checkbox",
          "required": true,
          "options": null,
          "icon": null,
          "multiline": null,
          "min": null,
          "max": null
        },
        {
          "name": "recognitionImpact",
          "label": "Can you provide an example of a time when recognition positively impacted your work?",
          "type": "text",
          "required": false,
          "options": null,
          "icon": null,
          "multiline": true,
          "min": null,
          "max": null
        },
        {
          "name": "programAccessibility",
          "label": "How accessible do you find the reward and recognition programs?",
          "type": "multiple",
          "required": true,
          "options": [
            "Very Accessible",
            "Accessible",
            "Somewhat Accessible",
            "Not Accessible"
          ],
          "icon": null,
          "multiline": null,
          "min": null,
          "max": null
        },
        {
          "name": "additionalFeedback",
          "label": "Any additional feedback or comments on the reward and recognition programs?",
          "type": "text",
          "required": false,
          "options": null,
          "icon": null,
          "multiline": true,
          "min": null,
          "max": null
        }
      ]
    }]
</survey_structure>

<survey_answers>
[
  {
    "programAwareness": "Very Aware",
    "programSatisfaction": 8,
    "fairness": "Fair",
    "motivationImpact": 4,
    "recognitionFrequency": "Often",
    "preferredRecognitionType": "Public Acknowledgment",
    "programEffectiveness": 4,
    "improvementSuggestions": "Increase the variety of rewards offered.",
    "peerRecognition": true,
    "managerRecognition": "Often",
    "programClarity": true,
    "recognitionImpact": "Being recognized publicly boosted my confidence and motivated me to take on more responsibilities.",
    "programAccessibility": "Very Accessible",
    "additionalFeedback": "Overall, the programs are effective but could benefit from more personalized rewards."
  },
  {
    "programAwareness": "Somewhat Aware",
    "programSatisfaction": 6,
    "fairness": "Neutral",
    "motivationImpact": 3,
    "recognitionFrequency": "Sometimes",
    "preferredRecognitionType": "Private Praise",
    "programEffectiveness": 3,
    "improvementSuggestions": "Provide clearer criteria for recognition.",
    "peerRecognition": false,
    "managerRecognition": "Sometimes",
    "programClarity": false,
    "recognitionImpact": "",
    "programAccessibility": "Accessible",
    "additionalFeedback": "I would appreciate more frequent recognition from my manager."
  },
  {
    "programAwareness": "Not Very Aware",
    "programSatisfaction": 4,
    "fairness": "Unfair",
    "motivationImpact": 2,
    "recognitionFrequency": "Rarely",
    "preferredRecognitionType": "Monetary Rewards",
    "programEffectiveness": 2,
    "improvementSuggestions": "Ensure that all departments have equal opportunities for recognition.",
    "peerRecognition": true,
    "managerRecognition": "Rarely",
    "programClarity": false,
    "recognitionImpact": "",
    "programAccessibility": "Somewhat Accessible",
    "additionalFeedback": "The current recognition process feels biased and inconsistent."
  },
  {
    "programAwareness": "Very Aware",
    "programSatisfaction": 9,
    "fairness": "Very Fair",
    "motivationImpact": 5,
    "recognitionFrequency": "Very Often",
    "preferredRecognitionType": "Career Advancement Opportunities",
    "programEffectiveness": 5,
    "improvementSuggestions": "",
    "peerRecognition": true,
    "managerRecognition": "Very Often",
    "programClarity": true,
    "recognitionImpact": "Recognition from both peers and management has significantly enhanced my performance and job satisfaction.",
    "programAccessibility": "Very Accessible",
    "additionalFeedback": "Keep up the great work! The programs are highly motivating."
  },
  {
    "programAwareness": "Not Aware at All",
    "programSatisfaction": 2,
    "fairness": "Very Unfair",
    "motivationImpact": 1,
    "recognitionFrequency": "Never",
    "preferredRecognitionType": "Other",
    "programEffectiveness": 1,
    "improvementSuggestions": "Implement a transparent and inclusive recognition system.",
    "peerRecognition": false,
    "managerRecognition": "Never",
    "programClarity": false,
    "recognitionImpact": "",
    "programAccessibility": "Not Accessible",
    "additionalFeedback": "There is a complete lack of recognition, which affects morale negatively."
  }]

</survey_answers>"""

    formatted_request = {
        "model": "claude-3-5-sonnet-latest",
        "messages": [
            {
                "role": "user",
                "content": user_message
            }
        ],
        "system": SYSTEM_MESSAGE,
        "max_tokens": 4096,
        "stream": True,
        "temperature": 0.1,
    }



    logger.debug(f"Sending request to Anthropic: {json.dumps(formatted_request, indent=2)}")

    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                    "POST",
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                        "accept": "text/event-stream",
                    },
                    json=formatted_request,
                    timeout=None
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    logger.error(f"Anthropic API error: {response.status_code} - {error_body}")
                    error_event = {
                        "type": "error",
                        "error": {"message": f"Anthropic API error: {response.status_code} - {error_body.decode()}"}
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                    return

                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield f"{line}\n\n"

        except Exception as e:
            logger.error(f"Error in stream_anthropic_response: {str(e)}")
            error_event = {
                "type": "error",
                "error": {"message": str(e)}
            }
            yield f"data: {json.dumps(error_event)}\n\n"


@stream_router.post("/anthropic")
async def proxy_anthropic(request: SurveyRequest) -> StreamingResponse:
    try:
        logger.debug(f"Received request: {request}")

        return StreamingResponse(
            stream_anthropic_response(request.survey_type, request.custom_prompt),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"Error in proxy_anthropic: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
