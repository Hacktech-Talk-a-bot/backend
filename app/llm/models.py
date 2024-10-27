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
    keywords: List[str] = Field(
        ...,
        description="List of keywords for survey generation",
        example=["office party", "celebration", "design"]
    )
