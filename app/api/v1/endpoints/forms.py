from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import form
from app.schemas.form import FormField, FormFieldCreate, FieldType, FieldTypeCreate

router = APIRouter()


@router.post("/field-types/", response_model=FieldType)
def create_field_type(
        field_type: FieldTypeCreate,
        db: Session = Depends(deps.get_db)
):
    return form.create_field_type(db=db, field_type=field_type)


@router.get("/field-types/", response_model=List[FieldType])
def read_field_types(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(deps.get_db)
):
    return form.get_field_types(db, skip=skip, limit=limit)


@router.post("/fields/", response_model=FormField)
def create_form_field(
        field: FormFieldCreate,
        db: Session = Depends(deps.get_db)
):
    return form.create_form_field(db=db, field=field)


@router.get("/fields/", response_model=List[FormField])
def read_form_fields(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(deps.get_db)
):
    return form.get_form_fields(db, skip=skip, limit=limit)
