from http.client import HTTPException

from sqlalchemy.orm import Session

from app.models.form import FieldType, FormField
from app.schemas.form import FieldTypeCreate, FormFieldCreate, FormSection, FormSectionCreate


def create_field_type(db: Session, field_type: FieldTypeCreate):
    db_field_type = FieldType(**field_type.dict())
    db.add(db_field_type)
    db.commit()
    db.refresh(db_field_type)
    return db_field_type


def get_field_types(db: Session, skip: int = 0, limit: int = 100):
    return db.query(FieldType).offset(skip).limit(limit).all()


def create_form_field(db: Session, field: FormFieldCreate):
    db_field = FormField(**field.dict())
    db.add(db_field)
    db.commit()
    db.refresh(db_field)
    return db_field


def get_form_fields(db: Session, skip: int = 0, limit: int = 100):
    return db.query(FormField).offset(skip).limit(limit).all()


def create_section(db: Session, section: FormSectionCreate) -> FormSection:
    db_section = FormSection(**section.dict())
    db.add(db_section)
    db.commit()
    db.refresh(db_section)
    return db_section


def get_section(db: Session, section_id: int) -> FormSection:
    section = db.query(FormSection).filter(FormSection.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    return section


def get_sections(
        db: Session,
        skip: int = 0,
        limit: int = 100
) -> list[FormSection]:
    return db.query(FormSection).offset(skip).limit(limit).all()


def update_section(
        db: Session,
        section_id: int,
        section_data: FormSectionCreate
) -> FormSection:
    db_section = get_section(db, section_id)
    for key, value in section_data.dict().items():
        setattr(db_section, key, value)
    db.commit()
    db.refresh(db_section)
    return db_section


def delete_section(db: Session, section_id: int) -> FormSection:
    db_section = get_section(db, section_id)
    db.delete(db_section)
    db.commit()
    return db_section
