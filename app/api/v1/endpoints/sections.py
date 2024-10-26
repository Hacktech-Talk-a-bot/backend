from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import form
from app.schemas.form import FormSection, FormSectionCreate

router = APIRouter()


@router.post("/", response_model=FormSection, status_code=status.HTTP_201_CREATED)
def create_form_section(
        section: FormSectionCreate,
        db: Session = Depends(deps.get_db)
):
    """
    Create a new form section.
    """
    return form.create_section(db=db, section=section)


@router.get("/{section_id}", response_model=FormSection)
def read_form_section(
        section_id: int,
        db: Session = Depends(deps.get_db)
):
    """
    Get a specific form section by ID.
    """
    return form.get_section(db=db, section_id=section_id)


@router.get("/", response_model=List[FormSection])
def read_form_sections(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(deps.get_db)
):
    """
    Get all form sections with pagination.
    """
    return form.get_sections(db=db, skip=skip, limit=limit)


@router.put("/{section_id}", response_model=FormSection)
def update_form_section(
        section_id: int,
        section: FormSectionCreate,
        db: Session = Depends(deps.get_db)
):
    """
    Update a form section.
    """
    return form.update_section(
        db=db,
        section_id=section_id,
        section_data=section
    )


@router.delete("/{section_id}", response_model=FormSection)
def delete_form_section(
        section_id: int,
        db: Session = Depends(deps.get_db)
):
    """
    Delete a form section.
    """
    return form.delete_section(db=db, section_id=section_id)
