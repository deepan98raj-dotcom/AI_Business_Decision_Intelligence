
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
import pymupdf


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

ALLOWED_DATA_EXTENSIONS = {".csv", ".xlsx", ".xls"}
ALLOWED_EXTENSIONS = ALLOWED_DATA_EXTENSIONS | {".pdf"}

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_ROWS = 100_000

REQUIRED_COLUMNS = {
    "sales": {
        "order_id",
        "order_date",
        "product",
        "quantity",
        "unit_price",
    },
    "customer_feedback": {
        "feedback_id",
        "feedback_date",
        "feedback",
    },
}


class IngestionError(ValueError):
    """An expected upload or data-processing error."""


def ensure_directories() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def safe_filename(filename: str) -> str:
    """Remove path components and unsafe characters from a filename."""
    name = Path(filename.replace("\\", "/")).name
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    name = name.lstrip(".")
    return name[:120] or "upload"


def validate_upload(filename: str, content: bytes) -> str:
    if not filename or not filename.strip():
        raise IngestionError("A filename is required.")

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise IngestionError(
            "Unsupported file type. Upload CSV, XLSX, XLS, or PDF."
        )

    if not content:
        raise IngestionError("The uploaded file is empty.")

    if len(content) > MAX_UPLOAD_BYTES:
        raise IngestionError("File exceeds the 15 MB upload limit.")

    # Basic signature checks. These do not replace full parser validation.
    if extension == ".pdf" and not content.lstrip().startswith(b"%PDF-"):
        raise IngestionError("The file does not appear to be a valid PDF.")

    if extension in {".xlsx", ".xls"} and not content.startswith(
        b"PK"
    ) and extension == ".xlsx":
        raise IngestionError("The file does not appear to be a valid XLSX.")

    return extension


def read_dataframe(content: bytes, extension: str) -> pd.DataFrame:
    from io import BytesIO

    stream = BytesIO(content)

    try:
        if extension == ".csv":
            df = pd.read_csv(stream, encoding="utf-8-sig")
        elif extension == ".xlsx":
            df = pd.read_excel(stream, engine="openpyxl")
        elif extension == ".xls":
            raise IngestionError(
                "Legacy XLS files are not enabled yet. "
                "Save the workbook as XLSX or CSV and upload it again."
            )
        else:
            raise IngestionError("This is not a structured-data file.")
    except IngestionError:
        raise
    except (ValueError, UnicodeError, OSError) as exc:
        raise IngestionError(
            f"Could not read the file: {exc}"
        ) from exc
    except Exception as exc:
        raise IngestionError(
            f"File parsing failed: {type(exc).__name__}: {exc}"
        ) from exc

    if df.empty:
        raise IngestionError("The file contains no data rows.")

    if len(df) > MAX_ROWS:
        raise IngestionError(
            f"File exceeds the {MAX_ROWS:,}-row processing limit."
        )

    if len(df.columns) > 200:
        raise IngestionError("The file exceeds the 200-column limit.")

    if len(df.columns) == 0:
        raise IngestionError("No columns were detected.")

    # Normalize headings and reject duplicate names after normalization.
    columns = [
        re.sub(r"\s+", "_", str(col).strip().lower())
        for col in df.columns
    ]

    if any(not col for col in columns):
        raise IngestionError("Blank column names are not allowed.")

    if len(columns) != len(set(columns)):
        raise IngestionError(
            "Column names are duplicated after normalization."
        )

    df.columns = columns
    return df


def clean_dataframe(
    df: pd.DataFrame,
    dataset_type: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if dataset_type not in {
        "sales",
        "customer_feedback",
        "general",
    }:
        raise IngestionError(
            "dataset_type must be sales, customer_feedback, or general."
        )

    original_rows = len(df)
    original_columns = len(df.columns)

    # Remove fully empty rows and duplicate records.
    df = df.dropna(how="all").copy()
    empty_rows_removed = original_rows - len(df)

    before_dedup = len(df)
    df = df.drop_duplicates().copy()
    duplicates_removed = before_dedup - len(df)

    # Trim whitespace in text columns without changing numeric values.
    for column in df.select_dtypes(include=["object", "string"]).columns:
        df[column] = df[column].map(
            lambda value: value.strip()
            if isinstance(value, str)
            else value
        )
        df[column] = df[column].replace("", pd.NA)

    required = REQUIRED_COLUMNS.get(dataset_type, set())
    missing_columns = sorted(required - set(df.columns))

    # Report schema problems without silently inventing missing data.
    warnings: list[str] = []
    if missing_columns:
        warnings.append(
            "Missing required columns: " + ", ".join(missing_columns)
        )

    invalid_numeric_counts: dict[str, int] = {}
    invalid_date_counts: dict[str, int] = {}

    if dataset_type == "sales":
        for column in ("quantity", "unit_price", "cost"):
            if column in df.columns:
                before = df[column].notna()
                converted = pd.to_numeric(df[column], errors="coerce")
                invalid_numeric_counts[column] = int(
                    (before & converted.isna()).sum()
                )
                df[column] = converted

        if "quantity" in df.columns:
            invalid = df["quantity"].notna() & (df["quantity"] <= 0)
            invalid_numeric_counts["quantity_nonpositive"] = int(invalid.sum())

        for column in ("order_date",):
            if column in df.columns:
                before = df[column].notna()
                converted = pd.to_datetime(df[column], errors="coerce")
                invalid_date_counts[column] = int(
                    (before & converted.isna()).sum()
                )
                df[column] = converted

        if {"quantity", "unit_price"}.issubset(df.columns):
            df["revenue"] = df["quantity"] * df["unit_price"]

            if "cost" in df.columns:
                df["total_cost"] = df["quantity"] * df["cost"]
                df["profit"] = df["revenue"] - df["total_cost"]

    elif dataset_type == "customer_feedback":
        if "feedback_date" in df.columns:
            before = df["feedback_date"].notna()
            converted = pd.to_datetime(
                df["feedback_date"], errors="coerce"
            )
            invalid_date_counts["feedback_date"] = int(
                (before & converted.isna()).sum()
            )
            df["feedback_date"] = converted

        if "feedback" in df.columns:
            df["feedback"] = df["feedback"].astype("string").str.strip()

        if "rating" in df.columns:
            df["rating"] = pd.to_numeric(
                df["rating"], errors="coerce"
            )
            invalid = df["rating"].notna() & ~df["rating"].between(1, 5)
            invalid_numeric_counts["rating_outside_1_to_5"] = int(
                invalid.sum()
            )

    if missing_columns:
        status = "invalid_schema"
    elif invalid_numeric_counts or invalid_date_counts:
        has_errors = any(invalid_numeric_counts.values()) or any(
            invalid_date_counts.values()
        )
        status = "needs_review" if has_errors else "valid"
    else:
        status = "valid"

    if invalid_numeric_counts:
        warnings.append(
            "Numeric conversion/validation counts: "
            + str(invalid_numeric_counts)
        )

    if invalid_date_counts:
        warnings.append(
            "Date conversion counts: " + str(invalid_date_counts)
        )

    report = {
        "dataset_type": dataset_type,
        "status": status,
        "original_rows": original_rows,
        "cleaned_rows": len(df),
        "empty_rows_removed": empty_rows_removed,
        "duplicates_removed": duplicates_removed,
        "column_count_before_cleaning": original_columns,
        "columns": list(df.columns),
        "missing_values_by_column": {
            str(key): int(value)
            for key, value in df.isna().sum().items()
        },
        "missing_required_columns": missing_columns,
        "invalid_numeric_counts": invalid_numeric_counts,
        "invalid_date_counts": invalid_date_counts,
        "warnings": warnings,
    }

    return df, report


def extract_pdf(content: bytes) -> dict[str, Any]:
    import pymupdf

    pages: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []

    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if document.is_encrypted:
                raise IngestionError(
                    "Password-protected PDFs are not supported."
                )

            if len(document) == 0:
                raise IngestionError("The PDF contains no pages.")

            if len(document) > 300:
                raise IngestionError("PDF exceeds the 300-page limit.")

            for page_number, page in enumerate(document, start=1):
                text = page.get_text("text")
                pages.append({
                    "page": page_number,
                    "text": text,
                    "character_count": len(text),
                })

                try:
                    finder = page.find_tables()
                    for table_index, table in enumerate(
                        finder.tables, start=1
                    ):
                        extracted = table.extract()
                        tables.append({
                            "page": page_number,
                            "table_index": table_index,
                            "rows": extracted,
                        })
                except Exception:
                    # Table detection can fail on pages without clear grids.
                    pass

    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError(
            f"PDF extraction failed: {type(exc).__name__}: {exc}"
        ) from exc

    return {
        "page_count": len(pages),
        "pages": pages,
        "tables_detected": len(tables),
        "tables": tables,
        "text_characters": sum(p["character_count"] for p in pages),
        "note": (
            "Scanned PDFs may require OCR. Table detection is best-effort "
            "and may not recover every visual table correctly."
        ),
    }


def save_upload(filename: str, content: bytes) -> Path:
    ensure_directories()
    safe_name = safe_filename(filename)
    # Unique prefix prevents accidental overwriting of prior uploads.
    import uuid

    destination = RAW_DIR / f"{uuid.uuid4().hex[:12]}_{safe_name}"
    destination.write_bytes(content)
    return destination


def save_processed_csv(df: pd.DataFrame, original_name: str) -> Path:
    ensure_directories()
    import uuid

    stem = Path(safe_filename(original_name)).stem
    destination = PROCESSED_DIR / (
        f"{uuid.uuid4().hex[:12]}_{stem}_cleaned.csv"
    )
    df.to_csv(destination, index=False)
    return destination


def preview_dataframe(
    df: pd.DataFrame,
    rows: int = 10,
) -> list[dict[str, Any]]:
    # Convert pandas-specific values to JSON-compatible values.
    safe_df = df.head(rows).astype(object).where(df.head(rows).notna(), None)
    return safe_df.to_dict(orient="records")
