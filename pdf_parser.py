import PyPDF2
import io

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text content from a PDF file
    
    Args:
        pdf_bytes: Raw bytes of the PDF file
        
    Returns:
        Extracted text as a string
        
    Raises:
        Exception: If PDF cannot be read or is empty
    """
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Check if PDF is encrypted
        if pdf_reader.is_encrypted:
            raise Exception("PDF is encrypted. Please provide an unencrypted file.")
        
        # Extract text from all pages
        text_parts = []
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            except Exception as e:
                # Continue even if one page fails
                print(f"Warning: Could not extract text from page {page_num + 1}: {e}")
                continue
        
        full_text = "\n\n".join(text_parts)
        
        if not full_text.strip():
            raise Exception("No text could be extracted from the PDF. It may be a scanned image or empty.")
        
        return full_text
        
    except PyPDF2.errors.PdfReadError as e:
        raise Exception(f"Invalid or corrupted PDF file: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing PDF: {str(e)}")
