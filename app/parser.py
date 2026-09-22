from pathlib import Path
import io
import pymupdf  # PyMuPDF

class ResumeParseError(Exception):
    pass

def extract_resume_text(filename: str, content: bytes) -> tuple[str, str | None]:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".txt"}:
        raise ResumeParseError("Only PDF and TXT resumes are supported.")

    if suffix == ".txt":
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ResumeParseError("TXT file is not valid UTF-8.") from exc
    else:
        try:
            doc = pymupdf.open(stream=content, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
        except Exception as exc:
            raise ResumeParseError(f"PDF could not be opened or parsed: {exc}") from exc

    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not text:
        return "", "The parser returned no readable text from this file."
    return text[:60000], None
