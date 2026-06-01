from fastapi import UploadFile, HTTPException, status
from pypdf import PdfReader
import logging

logger = logging.getLogger(__name__)


class PDFService:
    @staticmethod
    def extract_text(file: UploadFile) -> str:
        """
        FastAPI UploadFile nesnesinden ham metni güvenli bir şekilde ayıklar.
        İleride pypdf yerine başka bir kütüphaneye geçilirse sadece burası değişir.
        """
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Geçersiz dosya formatı. Sadece PDF dosyaları kabul edilir."
            )

        try:
            pdf_reader = PdfReader(file.file)
            full_text = ""

            for page_num, page in enumerate(pdf_reader.pages, start=1):
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

            logger.info(f"PDF başarıyla okundu: {file.filename} ({len(pdf_reader.pages)} sayfa)")

        except Exception as e:
            logger.error(f"PDF okunurken teknik hata oluştu ({file.filename}): {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF dosyası ayrıştırılamadı. Dosya bozuk veya şifreli olabilir."
            )

        if not full_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF içeriğinden anlamlı bir metin çıkarılamadı. Dosya taranmış bir resim (scanned) olabilir."
            )

        return full_text
