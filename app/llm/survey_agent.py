from fastapi import FastAPI, Body
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
import json

app = FastAPI()


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
