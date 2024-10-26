import uvicorn
from fastapi import FastAPI

from app.api.v1.endpoints import forms  # Add sections import
from app.core.config import settings
from app.core.database import Base, engine

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Dynamic Forms API")

# Include routers
app.include_router(
    forms.router,
    prefix=settings.API_V1_STR + "/forms",
    tags=["forms"]
)


#
# app.include_router(
#     sections.router,
#     prefix=settings.API_V1_STR + "/sections",
#     tags=["sections"]
# )


@app.get("/")
async def read_root():
    return {"message": "Welcome to Dynamic Forms API"}


def start():
    """Launched with `poetry run start` at root level"""
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
