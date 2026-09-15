from pydantic import BaseModel


class ResumeUploadResponse(BaseModel):
    filename: str
    extracted_text: str
    character_count: int
