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
# SCENARIO 1b: SUCCESSFUL MULTI-PAGE PDF EXTRACTION
# =====================================================================
def test_extract_text_multi_page_success():
    """
    GIVEN a valid PDF file with multiple pages of text content
    WHEN PDFService.extract_text is called
    THEN it should extract text from all pages and concatenate them.
    """
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "multi_page_invoice.pdf"
    mock_file.file = BytesIO(b"multi-page pdf content")

    with patch("src.pdf.pdf_service.PdfReader") as MockPdfReader:
        mock_reader_instance = MockPdfReader.return_value

        # Creating multiple page mocks with different text
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1: Order Details"

        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2: Payment Information"

        mock_page3 = MagicMock()
        mock_page3.extract_text.return_value = "Page 3: Shipping Address"

        mock_reader_instance.pages = [mock_page1, mock_page2, mock_page3]

        # Extract text
        result = PDFService.extract_text(mock_file)

        # Assertions
        assert "Page 1: Order Details" in result
        assert "Page 2: Payment Information" in result
        assert "Page 3: Shipping Address" in result
        assert mock_page1.extract_text.called
        assert mock_page2.extract_text.called
        assert mock_page3.extract_text.called


# =====================================================================
# SCENARIO 1c: PDF WITH MIXED EMPTY AND NON-EMPTY PAGES
# =====================================================================
def test_extract_text_mixed_page_content():
    """
    GIVEN a PDF with some empty pages and some pages with text
    WHEN PDFService.extract_text is called
    THEN it should extract text from all non-empty pages and skip empty ones gracefully.
    """
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "mixed_content.pdf"
    mock_file.file = BytesIO(b"mixed pdf")

    with patch("src.pdf.pdf_service.PdfReader") as MockPdfReader:
        mock_reader_instance = MockPdfReader.return_value

        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = ""  # Empty page

        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Valid Content"

        mock_page3 = MagicMock()
        mock_page3.extract_text.return_value = ""  # Another empty page

        mock_page4 = MagicMock()
        mock_page4.extract_text.return_value = "More Valid Content"

        mock_reader_instance.pages = [mock_page1, mock_page2, mock_page3, mock_page4]

        result = PDFService.extract_text(mock_file)

        assert "Valid Content" in result
        assert "More Valid Content" in result
        # The result should not be empty because at least some pages have content
        assert len(result.strip()) > 0


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
# SCENARIO 2b: VARIOUS INVALID EXTENSIONS
# =====================================================================
@pytest.mark.parametrize(
    "invalid_filename",
    [
        "document.docx",
        "image.png",
        "archive.zip",
        "spreadsheet.xlsx",
        "presentation.pptx",
        "file.txt",
        "data.csv",
    ],
)
def test_extract_text_various_invalid_extensions(invalid_filename):
    """
    GIVEN various files with non-PDF extensions
    WHEN PDFService.extract_text is called for each file
    THEN it should raise HTTPException 400 for all of them.
    """
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = invalid_filename

    with pytest.raises(HTTPException) as exc_info:
        PDFService.extract_text(mock_file)

    assert exc_info.value.status_code == 400


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
# SCENARIO 3b: ENCRYPTED PDF SPECIFIC ERROR
# =====================================================================
def test_extract_text_encrypted_pdf():
    """
    GIVEN an encrypted PDF file
    WHEN PdfReader raises an encryption-related exception
    THEN the service should catch it and raise a 400 HTTPException.
    """
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "encrypted_file.pdf"
    mock_file.file = BytesIO(b"encrypted content")

    with patch("src.pdf.pdf_service.PdfReader", side_effect=Exception("encrypted")):
        with pytest.raises(HTTPException) as exc_info:
            PDFService.extract_text(mock_file)

        assert exc_info.value.status_code == 400
        assert "could not be parsed" in exc_info.value.detail


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
        assert (
            "No meaningful text could be extracted from the PDF content."
            in exc_info.value.detail
        )


# =====================================================================
# SCENARIO 4b: PDF WITH ONLY WHITESPACE
# =====================================================================
def test_extract_text_whitespace_only_pdf():
    """
    GIVEN a PDF that contains only whitespace characters (spaces, tabs, newlines)
    WHEN PDFService.extract_text processes such a PDF
    THEN it should raise a 400 HTTPException because no meaningful content exists.
    """
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "whitespace_only.pdf"
    mock_file.file = BytesIO(b"whitespace pdf")

    with patch("src.pdf.pdf_service.PdfReader") as MockPdfReader:
        mock_reader_instance = MockPdfReader.return_value

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "   \n\t  \n   "  # Only whitespace
        mock_reader_instance.pages = [mock_page]

        with pytest.raises(HTTPException) as exc_info:
            PDFService.extract_text(mock_file)

        assert exc_info.value.status_code == 400
        assert "No meaningful text could be extracted" in exc_info.value.detail


# =====================================================================
# SCENARIO 5: REAL FILE INTEGRATION TEST
# =====================================================================
def test_extract_text_with_real_file():
    """
    GIVEN a real PDF file on the filesystem
    WHEN PDFService.extract_text is called with the file stream
    THEN it should successfully extract and return the textual content.
    """
    # Define the path to the real PDF file (tests/resources/example.pdf)
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, "resources", "example.pdf")

    # Ensure the test resource file actually exists
    assert os.path.exists(file_path), f"Test PDF file not found at: {file_path}"

    # Open the real file in binary read mode
    with open(file_path, "rb") as f:
        # Wrap the real file stream inside FastAPI's UploadFile object
        real_upload_file = UploadFile(filename="example.pdf", file=f)

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
