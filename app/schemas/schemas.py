# app/schemas/schemas.py
from typing import Optional, Dict, List, Any

from pydantic import BaseModel, Field
from typing_extensions import Annotated

# Custom type for form states
FormStateType = Annotated[str, Field(pattern='^(draft|started|finished)$')]
UserFormStateType = Annotated[str, Field(pattern='^(initial|in_progress|finished|analyzed)$')]


# User schemas
class UserBase(BaseModel):
    name: str
    category: str


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None


class User(UserBase):
    id: int

    class Config:
        from_attributes = True


# Form schemas
class FormBase(BaseModel):
    title: str
    description: str
    json_structure: Dict[str, Any]
    category: str


class FormCreate(FormBase):
    pass


class FormUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    json_structure: Optional[Dict[str, Any]] = None
    category: Optional[str] = None
    state: Optional[FormStateType] = None


class Form(FormBase):
    id: int
    state: FormStateType = Field(default="draft")

    class Config:
        from_attributes = True


# User-Form relationship schemas
class UserFormAssign(BaseModel):
    json_begin: Optional[Dict[str, Any]] = None


class UserFormUpdate(BaseModel):
    state: UserFormStateType
    json_response: Optional[Dict[str, Any]] = None


class UserFormResponse(BaseModel):
    form_id: int
    title: str
    description: str
    category: str
    form_state: str
    user_form_state: str
    json_begin: Optional[Dict[str, Any]]
    json_response: Optional[Dict[str, Any]]


# Response schemas for lists
class UserList(BaseModel):
    total: int
    users: List[User]


class FormList(BaseModel):
    total: int
    forms: List[Form]
