import os
from io import BytesIO

ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx'}

def validate_file(file_obj) -> bool:
    """Check if the uploaded file type is supported."""
    ext = os.path.splitext(file_obj.name)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def extract_text(file_obj) -> str:
    """Extract text from the uploaded file based on its extension."""
    ext = os.path.splitext(file_obj.name)[1].lower()
    file_obj.seek(0)
    
    if ext == '.txt':
        return file_obj.read().decode('utf-8', errors='replace')
        
    elif ext == '.pdf':
        try:
            import pypdf
            reader = pypdf.PdfReader(file_obj)
            text = []
            for page in reader.pages:
                text.append(page.extract_text() or '')
            return '\n'.join(text)
        except ImportError:
            return "Error: pypdf library not installed. Cannot extract PDF text."
        except Exception as e:
            return f"Error extracting PDF: {str(e)}"
            
    elif ext == '.docx':
        try:
            import docx
            doc = docx.Document(file_obj)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        except ImportError:
            return "Error: python-docx library not installed. Cannot extract DOCX text."
        except Exception as e:
            return f"Error extracting DOCX: {str(e)}"
            
    return ""

