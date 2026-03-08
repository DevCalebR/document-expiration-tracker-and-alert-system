from datetime import datetime
from pathlib import Path
from typing import List, Tuple
import re

from PIL import Image
from pdf2image import convert_from_path
from pytesseract import image_to_string
from sqlalchemy.orm import Session

from database import Document, DocumentDate
from storage import StorageError, get_storage_client, create_temp_file


def extract_text_from_file(file_path: Path):
    if not file_path.exists():
        return None, "File not found"

    ext = file_path.suffix.lower()
    try:
        content = []

        if ext == ".pdf":
            pdf_pages = convert_from_path(str(file_path))
            pages = len(pdf_pages)
            for i, page in enumerate(pdf_pages, start=1):
                page_text = image_to_string(page)
                content.append({"page": i, "text": page_text.strip()})
        elif ext in [".png", ".jpg", ".jpeg"]:
            img = Image.open(file_path)
            page_text = image_to_string(img)
            content.append({"page": 1, "text": page_text.strip()})
            pages = 1
        else:
            return None, "Unsupported file type for OCR"
    except Exception as exc:
        return None, str(exc)

    return {"pages": pages, "content": content}, None


def extract_dates(text_content: str):
    results = []
    date_patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
    ]

    matches = []
    for pattern in date_patterns:
        matches.extend(re.findall(pattern, text_content))

    for match in matches:
        iso_date = None
        detected_format = None
        parsed_dt = None
        for fmt_try in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                parsed_dt = datetime.strptime(match, fmt_try)
                iso_date = parsed_dt.date().isoformat()
                detected_format = fmt_try
                break
            except ValueError:
                continue

        if iso_date:
            today = datetime.utcnow().date()
            days_until_expiration = (parsed_dt.date() - today).days
            is_expired = days_until_expiration < 0
        else:
            days_until_expiration = None
            is_expired = None

        results.append(
            {
                "date_raw": match,
                "date_iso": iso_date,
                "detected_format": detected_format,
                "is_expired": is_expired,
                "days_until_expiration": days_until_expiration,
            }
        )

    return results


def process_documents(db: Session, documents: List[Document]):
    summary = []

    for doc in documents:
        storage = get_storage_client()
        temp_path = create_temp_file(Path(doc.original_filename).suffix or Path(doc.stored_filename).suffix)
        try:
            try:
                storage.download_to_path(doc.stored_filename, temp_path)
            except StorageError as exc:
                summary.append({"filename": doc.original_filename, "stored_filename": doc.stored_filename, "error": str(exc)})
                continue

            text_data, error = extract_text_from_file(temp_path)
        finally:
            try:
                temp_path.unlink()
            except OSError:
                pass
        if error:
            summary.append(
                {
                    "filename": doc.original_filename,
                    "stored_filename": doc.stored_filename,
                    "error": error,
                }
            )
            continue

        full_text = " ".join([p["text"] for p in text_data["content"]])
        dates_found = extract_dates(full_text)

        db.query(DocumentDate).filter(DocumentDate.document_id == doc.id).delete()
        for result in dates_found:
            db.add(
                DocumentDate(
                    document_id=doc.id,
                    date_raw=result.get("date_raw"),
                    date_iso=result.get("date_iso"),
                    detected_format=result.get("detected_format"),
                    is_expired=result.get("is_expired"),
                    days_until_expiration=result.get("days_until_expiration"),
                )
            )
        doc.last_processed_at = datetime.utcnow()
        db.commit()

        summary.append(
            {
                "filename": doc.original_filename,
                "stored_filename": doc.stored_filename,
                "pages_extracted": text_data["pages"],
                "dates_detected": len(dates_found),
                "results": dates_found,
            }
        )

    return summary
