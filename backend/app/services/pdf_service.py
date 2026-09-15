from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class InvalidPDFError(Exception):
    """Raised when the uploaded file is not a valid, readable PDF."""


class EmptyPDFTextError(Exception):
    """Raised when a valid PDF contains no extractable text."""


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text content from PDF file bytes.

    Raises:
        InvalidPDFError: if the bytes do not represent a readable PDF.
        EmptyPDFTextError: if the PDF is readable but yields no text
            (e.g. a scanned/image-only PDF).
    """
    try:
        reader = PdfReader(BytesIO(file_bytes))
        if reader.is_encrypted:
            raise InvalidPDFError("PDF is password-protected and cannot be read.")
        pages_text = [page.extract_text() or "" for page in reader.pages]
    except InvalidPDFError:
        raise
    except (PdfReadError, ValueError) as exc:
        raise InvalidPDFError(f"Could not read PDF file: {exc}") from exc

    extracted_text = "\n".join(pages_text).strip()
    if not extracted_text:
        raise EmptyPDFTextError("No extractable text found in the PDF.")

    return extracted_text
