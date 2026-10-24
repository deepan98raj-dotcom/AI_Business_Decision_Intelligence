
from pathlib import Path
import logging

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.schemas.ingestion import (
    PDFExtractionResponse,
    UploadResponse,
)
from app.services.ingestion_service import (
    MAX_UPLOAD_BYTES,
    IngestionError,
    clean_dataframe,
    extract_pdf,
    preview_dataframe,
    read_dataframe,
    save_processed_csv,
    save_upload,
    validate_upload,
)

router = APIRouter(
    prefix="/ingestion",
    tags=["Business Data Ingestion"],
)

logger = logging.getLogger(__name__)


async def read_limited_upload(upload: UploadFile) -> bytes:
    # Read at most one byte beyond the limit to detect oversized files.
    content = await upload.read(MAX_UPLOAD_BYTES + 1)

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 15 MB upload limit.",
        )

    return content


@router.post("/upload", response_model=UploadResponse)
async def upload_business_data(
    file: UploadFile = File(...),
    dataset_type: str = Query(
        default="general",
        description="sales, customer_feedback, or general",
    ),
):
    filename = file.filename or ""

    try:
        content = await read_limited_upload(file)
        extension = validate_upload(filename, content)

        if extension == ".pdf":
            raise IngestionError(
                "This endpoint accepts structured files only. "
                "Use /api/v1/ingestion/pdf for PDF documents."
            )

        raw_path = save_upload(filename, content)

        df = read_dataframe(content, extension)
        cleaned_df, report = clean_dataframe(df, dataset_type)

        processed_path = save_processed_csv(cleaned_df, filename)

        # Never describe an invalid schema as successfully validated.
        status = report["status"]
        if status == "invalid_schema":
            status = "needs_review"

        return UploadResponse(
            status=status,
            filename=raw_path.name,
            dataset_type=dataset_type,
            original_rows=report["original_rows"],
            cleaned_rows=report["cleaned_rows"],
            saved_processed_file=processed_path.name,
            validation_report=report,
            preview=preview_dataframe(cleaned_df),
        )

    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Business data ingestion failed")
        raise HTTPException(
            status_code=500,
            detail="Unexpected data-ingestion error. Check application logs.",
        ) from exc
    finally:
        await file.close()


@router.post("/pdf", response_model=PDFExtractionResponse)
async def upload_pdf_report(
    file: UploadFile = File(...),
):
    filename = file.filename or ""

    try:
        content = await read_limited_upload(file)
        extension = validate_upload(filename, content)

        if extension != ".pdf":
            raise IngestionError(
                "This endpoint accepts PDF files only."
            )

        raw_path = save_upload(filename, content)
        result = extract_pdf(content)

        # Keep an extraction artifact for later search/RAG development.
        import json

        output_path = raw_path.with_suffix(".extracted.json")
        output_path = (
            raw_path.parents[1]
            / "processed"
            / output_path.name
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return PDFExtractionResponse(
            status="processed",
            filename=raw_path.name,
            **result,
        )

    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("PDF extraction failed")
        raise HTTPException(
            status_code=500,
            detail="Unexpected PDF processing error. Check application logs.",
        ) from exc
    finally:
        await file.close()
