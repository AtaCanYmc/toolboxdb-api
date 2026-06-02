import pytest
from io import BytesIO
from fastapi import UploadFile, HTTPException
from unittest.mock import MagicMock, patch
from src.pdf import PDFService
import os


# =====================================================================
# SCENARIO 1: SUCCESSFUL PDF METADATA & TEXT EXTRACTION (HAPPY PATH)
# =====================================================================
def test_extract_text_success():
    """
    GIVEN a valid PDF file with text content
    WHEN PDFService.extract_text is called
    THEN it should successfully extract and return the full text content.
    """
    # Mocking FastAPI's UploadFile object
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "invoice_robotistan.pdf"
    # Providing an in-memory byte stream that PdfReader can process
    mock_file.file = BytesIO(b"dummy pdf content")

    # Patching PdfReader and its internal page structure
    with patch("src.pdf.pdf_service.PdfReader") as MockPdfReader:
        mock_reader_instance = MockPdfReader.return_value

        # Creating a single page mock that returns specific sample text
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "ESP32 Development Board x2"
        mock_reader_instance.pages = [mock_page]

        # Triggering the system under test (SUT)
        result = PDFService.extract_text(mock_file)

        # Assertions
        assert "ESP32" in result
        assert result.strip() == "ESP32 Development Board x2"
        mock_page.extract_text.assert_called_once()


# =====================================================================
# SCENARIO 2: INVALID FILE EXTENSION (EDGE CASE)
# =====================================================================
def test_extract_text_invalid_extension():
    """
    GIVEN a file with an unaccepted extension (e.g., .xlsx)
    WHEN PDFService.extract_text is called
    THEN it should raise an HTTPException with status code 400.
    """
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "invoice_data.xlsx"  # Invalid non-PDF extension

    # Expecting the function to raise an HTTPException
    with pytest.raises(HTTPException) as exc_info:
        PDFService.extract_text(mock_file)

    assert exc_info.value.status_code == 400
    assert "Invalid file format. Only PDF files are accepted!" in exc_info.value.detail


# =====================================================================
# SCENARIO 3: CORRUPTED OR ENCRYPTED PDF (ERROR HANDLING)
# =====================================================================
def test_extract_text_corrupted_pdf():
    """
    GIVEN a corrupted or unreadable PDF file
    WHEN PdfReader raises an unexpected parsing exception
    THEN the service should catch it and raise a descriptive 400 HTTPException.
    """
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "corrupted_file.pdf"
    mock_file.file = BytesIO(b"broken bytes")

    # Simulating a crash/exception inside PdfReader instantiation
    with patch("src.pdf.pdf_service.PdfReader", side_effect=Exception("Parsing Error")):
        with pytest.raises(HTTPException) as exc_info:
            PDFService.extract_text(mock_file)

        assert exc_info.value.status_code == 400
        assert "The PDF file could not be parsed" in exc_info.value.detail


# =====================================================================
# SCENARIO 4: SCANNED IMAGE OR EMPTY CONTENT (EDGE CASE)
# =====================================================================
def test_extract_text_empty_or_scanned_pdf():
    """
    GIVEN a scanned PDF containing only images without embedded text
    WHEN page.extract_text returns an empty string
    THEN it should raise a 400 HTTPException suggesting an OCR requirement.
    """
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "scanned_invoice.pdf"
    mock_file.file = BytesIO(b"scanned image pdf")

    with patch("src.pdf.pdf_service.PdfReader") as MockPdfReader:
        mock_reader_instance = MockPdfReader.return_value

        # Document contains pages but text extraction yields nothing (OCR baseline)
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""  # Empty text extraction result
        mock_reader_instance.pages = [mock_page]

        with pytest.raises(HTTPException) as exc_info:
            PDFService.extract_text(mock_file)

        assert exc_info.value.status_code == 400
        assert "No meaningful text could be extracted from the PDF content." in exc_info.value.detail


def test_extract_text_with_real_file():
    """
    GIVEN a real PDF file on the filesystem
    WHEN PDFService.extract_text is called with the file stream
    THEN it should successfully extract and return the textual content.
    """
    # Define the path to the real PDF file (tests/resources/ornek.pdf)
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, "resources", "example.pdf")

    # Ensure the test resource file actually exists
    assert os.path.exists(file_path), f"Test PDF file not found at: {file_path}"

    # Open the real file in binary read mode
    with open(file_path, "rb") as f:
        # Wrap the real file stream inside FastAPI's UploadFile object
        real_upload_file = UploadFile(
            filename="example.pdf",
            file=f
        )

        # Invoke the service to process the actual file content
        extracted_text = PDFService.extract_text(real_upload_file)

        # Print the output to the console (visible when running `pytest -v -s`)
        print("\n--- Extracted Real Text Start ---")
        print(extracted_text)
        print("--- Extracted Real Text End ---")

        # Assertions to validate the service output structure and content
        assert isinstance(extracted_text, str)
        assert len(extracted_text.strip()) > 0
        assert "If you can see this message PDFService works well." in extracted_text
