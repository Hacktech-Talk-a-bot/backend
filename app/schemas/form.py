# app/schemas/form.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class FieldOptionBase(BaseModel):
    value: str
    label: str
    order_index: int


class FieldOptionCreate(FieldOptionBase):
    field_id: int


class FieldOption(FieldOptionBase):
    id: int
    field_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class FieldTypeBase(BaseModel):
    type_name: str
    config_schema: Optional[Dict[str, Any]] = None


class FieldTypeCreate(FieldTypeBase):
    pass


class FieldType(FieldTypeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class FormSectionBase(BaseModel):
    title: str
    order_index: int


class FormSectionCreate(FormSectionBase):
    pass


class FormSection(FormSectionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class FormFieldBase(BaseModel):
    name: str
    label: str
    required: bool = False
    order_index: int
    config: Optional[Dict[str, Any]] = None


class FormFieldCreate(FormFieldBase):
    section_id: int
    field_type_id: int


class FormField(FormFieldBase):
    id: int
    section_id: int
    field_type_id: int
    created_at: datetime
    options: List[FieldOption] = []

    class Config:
        from_attributes = True


class FormResponseBase(BaseModel):
    pass


class FormResponseCreate(FormResponseBase):
    pass


class FormResponse(FormResponseBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class FieldValueBase(BaseModel):
    value: str


class FieldValueCreate(FieldValueBase):
    field_id: int
    response_id: int


class FieldValue(FieldValueBase):
    id: int
    field_id: int
    response_id: int
    created_at: datetime

    class Config:
        from_attributes = True
