# app/models/form.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class FormSection(Base):
    __tablename__ = "form_sections"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    fields = relationship("FormField", back_populates="section")


class FieldType(Base):
    __tablename__ = "field_types"

    id = Column(Integer, primary_key=True, index=True)
    type_name = Column(String, unique=True, nullable=False)
    config_schema = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    fields = relationship("FormField", back_populates="field_type")


class FieldOption(Base):
    __tablename__ = "field_options"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("form_fields.id"), nullable=False)
    value = Column(String, nullable=False)
    label = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    field = relationship("FormField", back_populates="options")


class FormField(Base):
    __tablename__ = "form_fields"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("form_sections.id"), nullable=False)
    name = Column(String, nullable=False)
    label = Column(String, nullable=False)
    field_type_id = Column(Integer, ForeignKey("field_types.id"), nullable=False)
    required = Column(Boolean, default=False)
    order_index = Column(Integer, nullable=False)
    config = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    section = relationship("FormSection", back_populates="fields")
    field_type = relationship("FieldType", back_populates="fields")
    options = relationship("FieldOption", back_populates="field")


class FormResponse(Base):
    __tablename__ = "form_responses"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    values = relationship("FieldValue", back_populates="response")
    multiple_values = relationship("MultipleFieldValue", back_populates="response")


class FieldValue(Base):
    __tablename__ = "field_values"

    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("form_responses.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("form_fields.id"), nullable=False)
    value = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    response = relationship("FormResponse", back_populates="values")
    field = relationship("FormField")


class MultipleFieldValue(Base):
    __tablename__ = "multiple_field_values"

    response_id = Column(Integer, ForeignKey("form_responses.id"), nullable=False, primary_key=True)
    field_id = Column(Integer, ForeignKey("form_fields.id"), nullable=False, primary_key=True)
    option_id = Column(Integer, ForeignKey("field_options.id"), nullable=False, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    response = relationship("FormResponse", back_populates="multiple_values")
    field = relationship("FormField")
    option = relationship("FieldOption")
