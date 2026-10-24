
from typing import Any

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    status: str
    filename: str
    dataset_type: str
    original_rows: int
    cleaned_rows: int
    saved_processed_file: str | None = None
    validation_report: dict[str, Any] = Field(default_factory=dict)
    preview: list[dict[str, Any]] = Field(default_factory=list)


class PDFExtractionResponse(BaseModel):
    status: str
    filename: str
    page_count: int
    tables_detected: int
    text_characters: int
    pages: list[dict[str, Any]]
    tables: list[dict[str, Any]]
    note: str
