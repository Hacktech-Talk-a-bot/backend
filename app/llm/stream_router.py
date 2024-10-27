import json
import logging
import os
from typing import AsyncGenerator, Optional
from pydantic import BaseModel

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import List, Dict, Optional

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

# Define the few-shot examples structure
FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": '<survey_structure>[{title:"Reward and Recognition Feedback Survey",fields:[{name:"programAwareness",label:"How aware are you of the current reward and recognition programs in place?",type:"multiple",required:true,options:["Very Aware","Somewhat Aware","Not Very Aware","Not Aware at All"],icon:null,multiline:null,min:null,max:null},{name:"programSatisfaction",label:"How satisfied are you with the current reward and recognition programs?",type:"slider",required:true,options:null,icon:null,multiline:null,min:1,max:10},{name:"fairness",label:"Do you feel the reward and recognition process is fair?",type:"multiple",required:true,options:["Very Fair","Fair","Neutral","Unfair","Very Unfair"],icon:null,multiline:null,min:null,max:null},{name:"motivationImpact",label:"How much do the reward and recognition programs motivate you to perform better?",type:"slider",required:true,options:null,icon:null,multiline:null,min:1,max:5},{name:"recognitionFrequency",label:"How often do you receive recognition for your work?",type:"multiple",required:true,options:["Very Often","Often","Sometimes","Rarely","Never"],icon:null,multiline:null,min:null,max:null},{name:"preferredRecognitionType",label:"What type of recognition do you value the most?",type:"multiple",required:true,options:["Public Acknowledgment","Private Praise","Monetary Rewards","Career Advancement Opportunities","Other"],icon:null,multiline:null,min:null,max:null},{name:"programEffectiveness",label:"How effective do you think the current programs are in recognizing employee achievements?",type:"icon",required:true,options:null,icon:"faStar",multiline:null,min:null,max:null},{name:"improvementSuggestions",label:"What improvements would you suggest for the reward and recognition programs?",type:"text",required:false,options:null,icon:null,multiline:true,min:null,max:null},{name:"peerRecognition",label:"Do you feel encouraged to recognize your peers?",type:"checkbox",required:true,options:null,icon:null,multiline:null,min:null,max:null},{name:"managerRecognition",label:"How often does your manager recognize your contributions?",type:"multiple",required:true,options:["Very Often","Often","Sometimes","Rarely","Never"],icon:null,multiline:null,min:null,max:null},{name:"programClarity",label:"Is the criteria for receiving rewards and recognition clear to you?",type:"checkbox",required:true,options:null,icon:null,multiline:null,min:null,max:null},{name:"recognitionImpact",label:"Can you provide an example of a time when recognition positively impacted your work?",type:"text",required:false,options:null,icon:null,multiline:true,min:null,max:null},{name:"programAccessibility",label:"How accessible do you find the reward and recognition programs?",type:"multiple",required:true,options:["Very Accessible","Accessible","Somewhat Accessible","Not Accessible"],icon:null,multiline:null,min:null,max:null},{name:"additionalFeedback",label:"Any additional feedback or comments on the reward and recognition programs?",type:"text",required:false,options:null,icon:null,multiline:true,min:null,max:null}]}]</survey_structure><survey_answers>[{programAwareness:"Very Aware",programSatisfaction:8,fairness:"Fair",motivationImpact:4,recognitionFrequency:"Often",preferredRecognitionType:"Public Acknowledgment",programEffectiveness:4,improvementSuggestions:"Increase the variety of rewards offered.",peerRecognition:true,managerRecognition:"Often",programClarity:true,recognitionImpact:"Being recognized publicly boosted my confidence and motivated me to take on more responsibilities.",programAccessibility:"Very Accessible",additionalFeedback:"Overall, the programs are effective but could benefit from more personalized rewards."},{programAwareness:"Somewhat Aware",programSatisfaction:6,fairness:"Neutral",motivationImpact:3,recognitionFrequency:"Sometimes",preferredRecognitionType:"Private Praise",programEffectiveness:3,improvementSuggestions:"Provide clearer criteria for recognition.",peerRecognition:false,managerRecognition:"Sometimes",programClarity:false,recognitionImpact:"",programAccessibility:"Accessible",additionalFeedback:"I would appreciate more frequent recognition from my manager."},{programAwareness:"Not Very Aware",programSatisfaction:4,fairness:"Unfair",motivationImpact:2,recognitionFrequency:"Rarely",preferredRecognitionType:"Monetary Rewards",programEffectiveness:2,improvementSuggestions:"Ensure that all departments have equal opportunities for recognition.",peerRecognition:true,managerRecognition:"Rarely",programClarity:false,recognitionImpact:"",programAccessibility:"Somewhat Accessible",additionalFeedback:"The current recognition process feels biased and inconsistent."},{programAwareness:"Very Aware",programSatisfaction:9,fairness:"Very Fair",motivationImpact:5,recognitionFrequency:"Very Often",preferredRecognitionType:"Career Advancement Opportunities",programEffectiveness:5,improvementSuggestions:"",peerRecognition:true,managerRecognition:"Very Often",programClarity:true,recognitionImpact:"Recognition from both peers and management has significantly enhanced my performance and job satisfaction.",programAccessibility:"Very Accessible",additionalFeedback:"Keep up the great work! The programs are highly motivating."},{programAwareness:"Not Aware at All",programSatisfaction:2,fairness:"Very Unfair",motivationImpact:1,recognitionFrequency:"Never",preferredRecognitionType:"Other",programEffectiveness:1,improvementSuggestions:"Implement a transparent and inclusive recognition system.",peerRecognition:false,managerRecognition:"Never",programClarity:false,recognitionImpact:"",programAccessibility:"Not Accessible",additionalFeedback:"There is a complete lack of recognition, which affects morale negatively."}]</survey_answers>'
    },
    {
        "role": "assistant",
        "content": "<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>Reward and Recognition Survey Results</title><link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css' rel='stylesheet'><style>.dashboard-container{padding:2rem;background-color:#f8f9fa;}.metric-card{background:white;border-radius:8px;padding:1.5rem;margin-bottom:1.5rem;box-shadow:0 2px 4px rgba(0,0,0,0.1);}.metric-title{color:#495057;font-size:1.1rem;margin-bottom:1rem;font-weight:600;}.satisfaction-meter{height:30px;background:linear-gradient(to right,#ff4e50,#f9d423,#28a745);border-radius:15px;position:relative;}.satisfaction-marker{width:20px;height:20px;background:white;border:3px solid #495057;border-radius:50%;position:absolute;top:5px;transform:translateX(-50%);}.progress-custom{height:25px;margin-bottom:0.5rem;}.progress-label{margin-bottom:0.25rem;display:flex;justify-content:space-between;}.star-rating{color:#ffd700;font-size:1.5rem;}.text-responses{max-height:300px;overflow-y:auto;}.response-item{padding:0.75rem;border-left:4px solid #007bff;background:#f8f9fa;margin-bottom:0.5rem;}</style></head><body><div class='dashboard-container'><h1 class='mb-4'>Reward and Recognition Survey Results</h1><div class='row'><div class='col-md-6'><div class='metric-card'><div class='metric-title'>Program Awareness Levels</div><div class='progress-label'><span>Very Aware</span><span>40%</span></div><div class='progress progress-custom'><div class='progress-bar bg-success' style='width: 40%'></div></div><div class='progress-label'><span>Somewhat Aware</span><span>20%</span></div><div class='progress progress-custom'><div class='progress-bar bg-info' style='width: 20%'></div></div><div class='progress-label'><span>Not Very Aware</span><span>20%</span></div><div class='progress progress-custom'><div class='progress-bar bg-warning' style='width: 20%'></div></div><div class='progress-label'><span>Not Aware at All</span><span>20%</span></div><div class='progress progress-custom'><div class='progress-bar bg-danger' style='width: 20%'></div></div></div></div><div class='col-md-6'><div class='metric-card'><div class='metric-title'>Overall Program Satisfaction</div><div class='satisfaction-meter'><div class='satisfaction-marker' style='left: 58%'></div></div><div class='text-center mt-2'><small>Average Score: 5.8/10</small></div></div></div><div class='col-md-6'><div class='metric-card'><div class='metric-title'>Recognition Frequency</div><div class='progress-label'><span>Very Often</span><span>20%</span></div><div class='progress progress-custom'><div class='progress-bar bg-success' style='width: 20%'></div></div><div class='progress-label'><span>Often</span><span>20%</span></div><div class='progress progress-custom'><div class='progress-bar bg-info' style='width: 20%'></div></div><div class='progress-label'><span>Sometimes</span><span>20%</span></div><div class='progress progress-custom'><div class='progress-bar bg-warning' style='width: 20%'></div></div><div class='progress-label'><span>Rarely/Never</span><span>40%</span></div><div class='progress progress-custom'><div class='progress-bar bg-danger' style='width: 40%'></div></div></div></div><div class='col-md-6'><div class='metric-card'><div class='metric-title'>Preferred Recognition Types</div><div class='progress-label'><span>Public Acknowledgment</span><span>20%</span></div><div class='progress progress-custom'><div class='progress-bar bg-primary' style='width: 20%'></div></div><div class='progress-label'><span>Private Praise</span><span>20%</span></div><div class='progress progress-custom'><div class='progress-bar bg-success' style='width: 20%'></div></div><div class='progress-label'><span>Monetary Rewards</span><span>20%</span></div><div class='progress progress-custom'><div class='progress-bar bg-info' style='width: 20%'></div></div><div class='progress-label'><span>Career Advancement</span><span>20%</span></div><div class='progress progress-custom'><div class='progress-bar bg-warning' style='width: 20%'></div></div></div></div><div class='col-md-6'><div class='metric-card'><div class='metric-title'>Program Effectiveness Rating</div><div class='star-rating text-center'>★★★★☆<div class='mt-2'><small>Average Rating: 3.0/5</small></div></div></div></div><div class='col-md-6'><div class='metric-card'><div class='metric-title'>Program Clarity & Accessibility</div><div class='d-flex justify-content-around text-center'><div><h4>40%</h4><p>Find criteria clear</p></div><div><h4>60%</h4><p>Find programs accessible</p></div></div></div></div><div class='col-12'><div class='metric-card'><div class='metric-title'>Key Feedback & Suggestions</div><div class='text-responses'><div class='response-item'>\"Increase the variety of rewards offered.\"</div><div class='response-item'>\"Provide clearer criteria for recognition.\"</div><div class='response-item'>\"Ensure that all departments have equal opportunities for recognition.\"</div><div class='response-item'>\"Implement a transparent and inclusive recognition system.\"</div></div></div></div></div></div></body></html>"
    },
    {
        "role": '<survey_structure>[{title:"Reward and Recognition Feedback Survey",fields:[{name:"programAwareness",label:"How aware are you of the current reward and recognition programs in place?",type:"multiple",required:true,options:["Very Aware","Somewhat Aware","Not Very Aware","Not Aware at All"],icon:null,multiline:null,min:null,max:null},{name:"programSatisfaction",label:"How satisfied are you with the current reward and recognition programs?",type:"slider",required:true,options:null,icon:null,multiline:null,min:1,max:10},{name:"fairness",label:"Do you feel the reward and recognition process is fair?",type:"multiple",required:true,options:["Very Fair","Fair","Neutral","Unfair","Very Unfair"],icon:null,multiline:null,min:null,max:null},{name:"motivationImpact",label:"How much do the reward and recognition programs motivate you to perform better?",type:"slider",required:true,options:null,icon:null,multiline:null,min:1,max:5},{name:"recognitionFrequency",label:"How often do you receive recognition for your work?",type:"multiple",required:true,options:["Very Often","Often","Sometimes","Rarely","Never"],icon:null,multiline:null,min:null,max:null},{name:"preferredRecognitionType",label:"What type of recognition do you value the most?",type:"multiple",required:true,options:["Public Acknowledgment","Private Praise","Monetary Rewards","Career Advancement Opportunities","Other"],icon:null,multiline:null,min:null,max:null},{name:"programEffectiveness",label:"How effective do you think the current programs are in recognizing employee achievements?",type:"icon",required:true,options:null,icon:"faStar",multiline:null,min:null,max:null},{name:"improvementSuggestions",label:"What improvements would you suggest for the reward and recognition programs?",type:"text",required:false,options:null,icon:null,multiline:true,min:null,max:null},{name:"peerRecognition",label:"Do you feel encouraged to recognize your peers?",type:"checkbox",required:true,options:null,icon:null,multiline:null,min:null,max:null},{name:"managerRecognition",label:"How often does your manager recognize your contributions?",type:"multiple",required:true,options:["Very Often","Often","Sometimes","Rarely","Never"],icon:null,multiline:null,min:null,max:null},{name:"programClarity",label:"Is the criteria for receiving rewards and recognition clear to you?",type:"checkbox",required:true,options:null,icon:null,multiline:null,min:null,max:null},{name:"recognitionImpact",label:"Can you provide an example of a time when recognition positively impacted your work?",type:"text",required:false,options:null,icon:null,multiline:true,min:null,max:null},{name:"programAccessibility",label:"How accessible do you find the reward and recognition programs?",type:"multiple",required:true,options:["Very Accessible","Accessible","Somewhat Accessible","Not Accessible"],icon:null,multiline:null,min:null,max:null},{name:"additionalFeedback",label:"Any additional feedback or comments on the reward and recognition programs?",type:"text",required:false,options:null,icon:null,multiline:true,min:null,max:null}]}]</survey_structure><survey_answers>[{programAwareness:"Very Aware",programSatisfaction:8,fairness:"Fair",motivationImpact:4,recognitionFrequency:"Often",preferredRecognitionType:"Public Acknowledgment",programEffectiveness:4,improvementSuggestions:"Increase the variety of rewards offered.",peerRecognition:true,managerRecognition:"Often",programClarity:true,recognitionImpact:"Being recognized publicly boosted my confidence and motivated me to take on more responsibilities.",programAccessibility:"Very Accessible",additionalFeedback:"Overall, the programs are effective but could benefit from more personalized rewards."},{programAwareness:"Somewhat Aware",programSatisfaction:6,fairness:"Neutral",motivationImpact:3,recognitionFrequency:"Sometimes",preferredRecognitionType:"Private Praise",programEffectiveness:3,improvementSuggestions:"Provide clearer criteria for recognition.",peerRecognition:false,managerRecognition:"Sometimes",programClarity:false,recognitionImpact:"",programAccessibility:"Accessible",additionalFeedback:"I would appreciate more frequent recognition from my manager."},{programAwareness:"Not Very Aware",programSatisfaction:4,fairness:"Unfair",motivationImpact:2,recognitionFrequency:"Rarely",preferredRecognitionType:"Monetary Rewards",programEffectiveness:2,improvementSuggestions:"Ensure that all departments have equal opportunities for recognition.",peerRecognition:true,managerRecognition:"Rarely",programClarity:false,recognitionImpact:"",programAccessibility:"Somewhat Accessible",additionalFeedback:"The current recognition process feels biased and inconsistent."},{programAwareness:"Very Aware",programSatisfaction:9,fairness:"Very Fair",motivationImpact:5,recognitionFrequency:"Very Often",preferredRecognitionType:"Career Advancement Opportunities",programEffectiveness:5,improvementSuggestions:"",peerRecognition:true,managerRecognition:"Very Often",programClarity:true,recognitionImpact:"Recognition from both peers and management has significantly enhanced my performance and job satisfaction.",programAccessibility:"Very Accessible",additionalFeedback:"Keep up the great work! The programs are highly motivating."},{programAwareness:"Not Aware at All",programSatisfaction:2,fairness:"Very Unfair",motivationImpact:1,recognitionFrequency:"Never",preferredRecognitionType:"Other",programEffectiveness:1,improvementSuggestions:"Implement a transparent and inclusive recognition system.",peerRecognition:false,managerRecognition:"Never",programClarity:false,recognitionImpact:"",programAccessibility:"Not Accessible",additionalFeedback:"There is a complete lack of recognition, which affects morale negatively."}]</survey_answers>',
        "content": "What is the capital of Japan?"
    },
    {
        "role": "assistant",
        "content": "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"><title>Reward and Recognition Survey Results</title><link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css\" rel=\"stylesheet\"><style>.dashboard-container{padding:2rem;background:#f8f9fa;}.metric-card{background:white;border-radius:8px;padding:1.5rem;margin-bottom:1.5rem;box-shadow:0 2px 4px rgba(0,0,0,0.1);}.satisfaction-meter{height:30px;background:#e9ecef;border-radius:15px;overflow:hidden;margin:1rem 0;}.satisfaction-fill{height:100%;background:linear-gradient(90deg,#dc3545 0%,#ffc107 50%,#198754 100%);transition:width 0.3s ease;}.response-bar{height:24px;background:#0d6efd;border-radius:4px;margin:4px 0;}.star-rating{color:#ffc107;font-size:24px;}.awareness-chart{display:flex;flex-wrap:wrap;gap:10px;}.awareness-item{flex:1;min-width:150px;padding:1rem;border-radius:8px;text-align:center;color:white;}.text-feedback{background:#f8f9fa;border-left:4px solid #0d6efd;padding:1rem;margin:0.5rem 0;border-radius:0 4px 4px 0;}</style></head><body><div class=\"dashboard-container\"><h1 class=\"mb-4\">Reward and Recognition Survey Results</h1><div class=\"metric-card\"><h3>Program Awareness</h3><div class=\"awareness-chart\"><div class=\"awareness-item bg-success\"><h4>40%</h4><p>Very Aware</p></div><div class=\"awareness-item bg-info\"><h4>20%</h4><p>Somewhat Aware</p></div><div class=\"awareness-item bg-warning\"><h4>20%</h4><p>Not Very Aware</p></div><div class=\"awareness-item bg-danger\"><h4>20%</h4><p>Not Aware at All</p></div></div></div><div class=\"metric-card\"><h3>Program Satisfaction</h3><div class=\"satisfaction-meter\"><div class=\"satisfaction-fill\" style=\"width: 58%\"></div></div><div class=\"text-center\"><h4>Average Score: 5.8/10</h4></div></div><div class=\"metric-card\"><h3>Recognition Frequency</h3><div class=\"mb-3\"><div class=\"d-flex justify-content-between align-items-center\"><span>Very Often</span><div class=\"response-bar\" style=\"width: 20%\"></div><span>20%</span></div><div class=\"d-flex justify-content-between align-items-center\"><span>Often</span><div class=\"response-bar\" style=\"width: 20%\"></div><span>20%</span></div><div class=\"d-flex justify-content-between align-items-center\"><span>Sometimes</span><div class=\"response-bar\" style=\"width: 20%\"></div><span>20%</span></div><div class=\"d-flex justify-content-between align-items-center\"><span>Rarely</span><div class=\"response-bar\" style=\"width: 20%\"></div><span>20%</span></div><div class=\"d-flex justify-content-between align-items-center\"><span>Never</span><div class=\"response-bar\" style=\"width: 20%\"></div><span>20%</span></div></div></div><div class=\"metric-card\"><h3>Preferred Recognition Type</h3><div class=\"row\"><div class=\"col-md-3 text-center mb-3\"><div class=\"p-3 bg-light rounded\"><h4>20%</h4><p>Public Acknowledgment</p></div></div><div class=\"col-md-3 text-center mb-3\"><div class=\"p-3 bg-light rounded\"><h4>20%</h4><p>Private Praise</p></div></div><div class=\"col-md-3 text-center mb-3\"><div class=\"p-3 bg-light rounded\"><h4>20%</h4><p>Monetary Rewards</p></div></div><div class=\"col-md-3 text-center mb-3\"><div class=\"p-3 bg-light rounded\"><h4>40%</h4><p>Career Advancement</p></div></div></div></div><div class=\"metric-card\"><h3>Program Effectiveness</h3><div class=\"text-center\"><div class=\"star-rating\">★★★★☆</div><p class=\"mt-2\">Average Rating: 3 out of 5</p></div></div><div class=\"metric-card\"><h3>Key Feedback</h3><div class=\"text-feedback\">\"Being recognized publicly boosted my confidence and motivated me to take on more responsibilities.\"</div><div class=\"text-feedback\">\"Provide clearer criteria for recognition.\"</div><div class=\"text-feedback\">\"Ensure that all departments have equal opportunities for recognition.\"</div></div><div class=\"metric-card\"><h3>Program Clarity and Accessibility</h3><div class=\"row\"><div class=\"col-md-6\"><h5>Clear Criteria</h5><div class=\"progress\"><div class=\"progress-bar\" role=\"progressbar\" style=\"width: 40%;\" aria-valuenow=\"40\" aria-valuemin=\"0\" aria-valuemax=\"100\">40%</div></div></div><div class=\"col-md-6\"><h5>Accessible Programs</h5><div class=\"progress\"><div class=\"progress-bar bg-success\" role=\"progressbar\" style=\"width: 60%;\" aria-valuenow=\"60\" aria-valuemin=\"0\" aria-valuemax=\"100\">60%</div></div></div></div></div></body></html>"
    },
    {
        "role": '<survey_structure>[{title:"Reward and Recognition Feedback Survey",fields:[{name:"programAwareness",label:"How aware are you of the current reward and recognition programs in place?",type:"multiple",required:true,options:["Very Aware","Somewhat Aware","Not Very Aware","Not Aware at All"],icon:null,multiline:null,min:null,max:null},{name:"programSatisfaction",label:"How satisfied are you with the current reward and recognition programs?",type:"slider",required:true,options:null,icon:null,multiline:null,min:1,max:10},{name:"fairness",label:"Do you feel the reward and recognition process is fair?",type:"multiple",required:true,options:["Very Fair","Fair","Neutral","Unfair","Very Unfair"],icon:null,multiline:null,min:null,max:null},{name:"motivationImpact",label:"How much do the reward and recognition programs motivate you to perform better?",type:"slider",required:true,options:null,icon:null,multiline:null,min:1,max:5},{name:"recognitionFrequency",label:"How often do you receive recognition for your work?",type:"multiple",required:true,options:["Very Often","Often","Sometimes","Rarely","Never"],icon:null,multiline:null,min:null,max:null},{name:"preferredRecognitionType",label:"What type of recognition do you value the most?",type:"multiple",required:true,options:["Public Acknowledgment","Private Praise","Monetary Rewards","Career Advancement Opportunities","Other"],icon:null,multiline:null,min:null,max:null},{name:"programEffectiveness",label:"How effective do you think the current programs are in recognizing employee achievements?",type:"icon",required:true,options:null,icon:"faStar",multiline:null,min:null,max:null},{name:"improvementSuggestions",label:"What improvements would you suggest for the reward and recognition programs?",type:"text",required:false,options:null,icon:null,multiline:true,min:null,max:null},{name:"peerRecognition",label:"Do you feel encouraged to recognize your peers?",type:"checkbox",required:true,options:null,icon:null,multiline:null,min:null,max:null},{name:"managerRecognition",label:"How often does your manager recognize your contributions?",type:"multiple",required:true,options:["Very Often","Often","Sometimes","Rarely","Never"],icon:null,multiline:null,min:null,max:null},{name:"programClarity",label:"Is the criteria for receiving rewards and recognition clear to you?",type:"checkbox",required:true,options:null,icon:null,multiline:null,min:null,max:null},{name:"recognitionImpact",label:"Can you provide an example of a time when recognition positively impacted your work?",type:"text",required:false,options:null,icon:null,multiline:true,min:null,max:null},{name:"programAccessibility",label:"How accessible do you find the reward and recognition programs?",type:"multiple",required:true,options:["Very Accessible","Accessible","Somewhat Accessible","Not Accessible"],icon:null,multiline:null,min:null,max:null},{name:"additionalFeedback",label:"Any additional feedback or comments on the reward and recognition programs?",type:"text",required:false,options:null,icon:null,multiline:true,min:null,max:null}]}]</survey_structure><survey_answers>[{programAwareness:"Very Aware",programSatisfaction:8,fairness:"Fair",motivationImpact:4,recognitionFrequency:"Often",preferredRecognitionType:"Public Acknowledgment",programEffectiveness:4,improvementSuggestions:"Increase the variety of rewards offered.",peerRecognition:true,managerRecognition:"Often",programClarity:true,recognitionImpact:"Being recognized publicly boosted my confidence and motivated me to take on more responsibilities.",programAccessibility:"Very Accessible",additionalFeedback:"Overall, the programs are effective but could benefit from more personalized rewards."},{programAwareness:"Somewhat Aware",programSatisfaction:6,fairness:"Neutral",motivationImpact:3,recognitionFrequency:"Sometimes",preferredRecognitionType:"Private Praise",programEffectiveness:3,improvementSuggestions:"Provide clearer criteria for recognition.",peerRecognition:false,managerRecognition:"Sometimes",programClarity:false,recognitionImpact:"",programAccessibility:"Accessible",additionalFeedback:"I would appreciate more frequent recognition from my manager."},{programAwareness:"Not Very Aware",programSatisfaction:4,fairness:"Unfair",motivationImpact:2,recognitionFrequency:"Rarely",preferredRecognitionType:"Monetary Rewards",programEffectiveness:2,improvementSuggestions:"Ensure that all departments have equal opportunities for recognition.",peerRecognition:true,managerRecognition:"Rarely",programClarity:false,recognitionImpact:"",programAccessibility:"Somewhat Accessible",additionalFeedback:"The current recognition process feels biased and inconsistent."},{programAwareness:"Very Aware",programSatisfaction:9,fairness:"Very Fair",motivationImpact:5,recognitionFrequency:"Very Often",preferredRecognitionType:"Career Advancement Opportunities",programEffectiveness:5,improvementSuggestions:"",peerRecognition:true,managerRecognition:"Very Often",programClarity:true,recognitionImpact:"Recognition from both peers and management has significantly enhanced my performance and job satisfaction.",programAccessibility:"Very Accessible",additionalFeedback:"Keep up the great work! The programs are highly motivating."},{programAwareness:"Not Aware at All",programSatisfaction:2,fairness:"Very Unfair",motivationImpact:1,recognitionFrequency:"Never",preferredRecognitionType:"Other",programEffectiveness:1,improvementSuggestions:"Implement a transparent and inclusive recognition system.",peerRecognition:false,managerRecognition:"Never",programClarity:false,recognitionImpact:"",programAccessibility:"Not Accessible",additionalFeedback:"There is a complete lack of recognition, which affects morale negatively."}]</survey_answers>',
        "content": "What is the capital of Japan?"
    },
    {
        "role": "assistant",
        "content": "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"><title>Reward and Recognition Survey Results</title><link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css\" rel=\"stylesheet\"><style>.dashboard-container{padding:2rem;background:#f8f9fa;}.metric-card{background:white;border-radius:8px;padding:1.5rem;margin-bottom:1.5rem;box-shadow:0 2px 4px rgba(0,0,0,0.1);}.satisfaction-meter{height:30px;background:#e9ecef;border-radius:15px;overflow:hidden;margin:1rem 0;}.satisfaction-fill{height:100%;background:linear-gradient(90deg,#dc3545 0%,#ffc107 50%,#198754 100%);transition:width 0.3s ease;}.response-bar{height:24px;background:#0d6efd;border-radius:4px;margin:4px 0;}.star-rating{color:#ffc107;font-size:24px;}.awareness-chart{display:flex;flex-wrap:wrap;gap:10px;}.awareness-item{flex:1;min-width:150px;padding:1rem;border-radius:8px;text-align:center;color:white;}.text-feedback{background:#f8f9fa;border-left:4px solid #0d6efd;padding:1rem;margin:0.5rem 0;border-radius:0 4px 4px 0;}</style></head><body><div class=\"dashboard-container\"><h1 class=\"mb-4\">Reward and Recognition Survey Results</h1><div class=\"metric-card\"><h3>Program Awareness</h3><div class=\"awareness-chart\"><div class=\"awareness-item bg-success\"><h4>40%</h4><p>Very Aware</p></div><div class=\"awareness-item bg-info\"><h4>20%</h4><p>Somewhat Aware</p></div><div class=\"awareness-item bg-warning\"><h4>20%</h4><p>Not Very Aware</p></div><div class=\"awareness-item bg-danger\"><h4>20%</h4><p>Not Aware at All</p></div></div></div><div class=\"metric-card\"><h3>Program Satisfaction</h3><div class=\"satisfaction-meter\"><div class=\"satisfaction-fill\" style=\"width: 58%\"></div></div><div class=\"text-center\"><h4>Average Score: 5.8/10</h4></div></div><div class=\"metric-card\"><h3>Recognition Frequency</h3><div class=\"mb-3\"><div class=\"d-flex justify-content-between align-items-center\"><span>Very Often</span><div class=\"response-bar\" style=\"width: 20%\"></div><span>20%</span></div><div class=\"d-flex justify-content-between align-items-center\"><span>Often</span><div class=\"response-bar\" style=\"width: 20%\"></div><span>20%</span></div><div class=\"d-flex justify-content-between align-items-center\"><span>Sometimes</span><div class=\"response-bar\" style=\"width: 20%\"></div><span>20%</span></div><div class=\"d-flex justify-content-between align-items-center\"><span>Rarely</span><div class=\"response-bar\" style=\"width: 20%\"></div><span>20%</span></div><div class=\"d-flex justify-content-between align-items-center\"><span>Never</span><div class=\"response-bar\" style=\"width: 20%\"></div><span>20%</span></div></div></div><div class=\"metric-card\"><h3>Preferred Recognition Type</h3><div class=\"row\"><div class=\"col-md-3 text-center mb-3\"><div class=\"p-3 bg-light rounded\"><h4>20%</h4><p>Public Acknowledgment</p></div></div><div class=\"col-md-3 text-center mb-3\"><div class=\"p-3 bg-light rounded\"><h4>20%</h4><p>Private Praise</p></div></div><div class=\"col-md-3 text-center mb-3\"><div class=\"p-3 bg-light rounded\"><h4>20%</h4><p>Monetary Rewards</p></div></div><div class=\"col-md-3 text-center mb-3\"><div class=\"p-3 bg-light rounded\"><h4>40%</h4><p>Career Advancement</p></div></div></div></div><div class=\"metric-card\"><h3>Program Effectiveness</h3><div class=\"text-center\"><div class=\"star-rating\">★★★★☆</div><p class=\"mt-2\">Average Rating: 3 out of 5</p></div></div><div class=\"metric-card\"><h3>Key Feedback</h3><div class=\"text-feedback\">\"Being recognized publicly boosted my confidence and motivated me to take on more responsibilities.\"</div><div class=\"text-feedback\">\"Provide clearer criteria for recognition.\"</div><div class=\"text-feedback\">\"Ensure that all departments have equal opportunities for recognition.\"</div></div><div class=\"metric-card\"><h3>Program Clarity and Accessibility</h3><div class=\"row\"><div class=\"col-md-6\"><h5>Clear Criteria</h5><div class=\"progress\"><div class=\"progress-bar\" role=\"progressbar\" style=\"width: 40%;\" aria-valuenow=\"40\" aria-valuemin=\"0\" aria-valuemax=\"100\">40%</div></div></div><div class=\"col-md-6\"><h5>Accessible Programs</h5><div class=\"progress\"><div class=\"progress-bar bg-success\" role=\"progressbar\" style=\"width: 60%;\" aria-valuenow=\"60\" aria-valuemin=\"0\" aria-valuemax=\"100\">60%</div></div></div></div></div></body></html>"
    }
]


def format_request(
        user_message: str,
        system_message: str,
        few_shot_examples: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1
) -> Dict:
    """
    Format the request for the Anthropic API with optional few-shot examples.

    Args:
        user_message: The user's input message
        system_message: The system message to guide Claude's behavior
        few_shot_examples: Optional list of example conversations
        max_tokens: Maximum tokens in response
        temperature: Response randomness (0-1)

    Returns:
        Dict containing the formatted request
    """
    messages = []

    # Add few-shot examples if provided
    if few_shot_examples:
        messages.extend(few_shot_examples)

    # Add the current user message
    messages.append({
        "role": "user",
        "content": user_message
    })

    return {
        "model": "claude-3-5-sonnet-latest",
        "messages": messages,
        "system": system_message,
        "max_tokens": max_tokens,
        "stream": True,
        "temperature": temperature,
    }


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


    formatted_request = format_request(
        user_message=user_message,
        system_message=SYSTEM_MESSAGE,
        few_shot_examples=FEW_SHOT_EXAMPLES
    )

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
