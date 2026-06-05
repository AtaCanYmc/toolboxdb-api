from fastapi import UploadFile, HTTPException, status
from pypdf import PdfReader
import logging

logger = logging.getLogger(__name__)


class PDFService:
    @staticmethod
    def extract_text(file: UploadFile) -> str:
        """
        Safely extracts raw text from the FastAPI UploadFile object.
        If we switch to a different library instead of pypdf in the future, only this part will change.
        """
        if not file.filename.endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. Only PDF files are accepted!",
            )

        try:
            pdf_reader = PdfReader(file.file)
            full_text = ""

            for page_num, page in enumerate(pdf_reader.pages, start=1):
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

            logger.info(
                f"The PDF was successfully read: {file.filename} ({len(pdf_reader.pages)} pages)"
            )

        except Exception as e:
            logger.error(
                f"An error occurred while opening the PDF ({file.filename}): {str(e)}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The PDF file could not be parsed. The file may be corrupted or encrypted.",
            )

        if not full_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No meaningful text could be extracted from the PDF content. The file may be a scanned image.",
            )

        return full_text
