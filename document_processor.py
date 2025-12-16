# document_processor.py
import PyPDF2
import docx
import requests
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image
import io
import re

class DocumentProcessor:
    def __init__(self):
        pass
    
    def extract_text_from_file(self, file_path):
        """Extract COMPLETE text from various file formats"""
        try:
            file_ext = file_path.lower().split('.')[-1]
            
            print(f"📄 Extracting text from {file_ext.upper()} file: {file_path}")
            
            if file_ext == 'pdf':
                text = self._extract_from_pdf(file_path)
            elif file_ext in ['doc', 'docx']:
                text = self._extract_from_docx(file_path)
            elif file_ext in ['jpg', 'jpeg', 'png', 'bmp', 'tiff']:
                text = self._extract_from_image(file_path)
            elif file_ext == 'txt':
                text = self._extract_from_txt(file_path)
            else:
                print(f"❌ Unsupported file format: {file_ext}")
                return None
            
            if text:
                text = self._clean_extracted_text(text)
                print(f"✅ Successfully extracted {len(text)} characters from {file_ext.upper()}")
                return text
            else:
                print(f"❌ No text extracted from {file_ext.upper()}")
                return None
                
        except Exception as e:
            print(f"❌ Error extracting text from file: {e}")
            return None
    
    def _extract_from_pdf(self, file_path):
        """Extract COMPLETE text from PDF with multiple fallback methods"""
        try:
            text = ""
            
            # Method 1: Try PyPDF2 first
            try:
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for i, page in enumerate(reader.pages):
                        page_text = page.extract_text()
                        if page_text:
                            text += f"--- Page {i+1} ---\n{page_text}\n\n"
                print(f"📖 PyPDF2 extracted {len(text)} characters")
            except Exception as e:
                print(f"⚠️ PyPDF2 failed: {e}")
                text = ""
            
            # If PyPDF2 didn't get much text, try alternative methods
            if len(text.strip()) < 100:
                print("🔄 PyPDF2 extraction seems incomplete, trying alternative methods...")
                
                # Method 2: Try pdfplumber if available
                try:
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        for i, page in enumerate(pdf.pages):
                            page_text = page.extract_text()
                            if page_text:
                                text += f"--- Page {i+1} ---\n{page_text}\n\n"
                    print(f"📖 pdfplumber extracted {len(text)} characters")
                except ImportError:
                    print("ℹ️ pdfplumber not installed, skipping")
                except Exception as e:
                    print(f"⚠️ pdfplumber failed: {e}")
            
            # Method 3: Last resort - try OCR if text is still minimal
            if len(text.strip()) < 50:
                print("🔄 Text extraction very low, attempting OCR...")
                try:
                    ocr_text = self._extract_from_image(file_path)  # Treat PDF as image for OCR
                    if ocr_text:
                        text += f"--- OCR Extracted Text ---\n{ocr_text}"
                except Exception as e:
                    print(f"⚠️ OCR fallback failed: {e}")
            
            return text.strip() if text and text.strip() else None
            
        except Exception as e:
            print(f"❌ All PDF extraction methods failed: {e}")
            return None
    
    def _extract_from_docx(self, file_path):
        """Extract COMPLETE text from DOCX including tables"""
        try:
            doc = docx.Document(file_path)
            text = ""
            
            # Extract paragraphs
            for paragraph in doc.paragraphs:
                if paragraph.text and paragraph.text.strip():
                    text += paragraph.text + "\n"
            
            # Extract tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text and cell.text.strip():
                            text += cell.text + " | "
                    text += "\n"
                text += "\n"
            
            return text.strip() if text and text.strip() else None
            
        except Exception as e:
            print(f"❌ Error reading DOCX: {e}")
            return None
    
    def _extract_from_image(self, file_path):
        """Extract text from image using OCR with improved settings"""
        try:
            image = Image.open(file_path)
            
            # Improve OCR by converting to grayscale and enhancing contrast
            if image.mode != 'L':
                image = image.convert('L')
            
            # OCR configuration for better text extraction
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?;:()[]{}@#$%^&*+-/=\|_~` '
            text = pytesseract.image_to_string(image, config=custom_config)
            
            return text.strip() if text and text.strip() else None
            
        except Exception as e:
            print(f"❌ Error reading image: {e}")
            return None
    
    def _extract_from_txt(self, file_path):
        """Extract text from TXT with multiple encoding attempts"""
        encodings = ['utf-8', 'latin-1', 'windows-1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    content = file.read()
                    if content and content.strip():
                        print(f"✅ TXT read successfully with {encoding} encoding")
                        return content.strip()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"⚠️ Failed to read TXT with {encoding}: {e}")
                continue
        
        print("❌ All encoding attempts failed for TXT file")
        return None
    
    def _clean_extracted_text(self, text):
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace but preserve paragraph structure
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Normalize multiple newlines
        text = re.sub(r'[ \t]+', ' ', text)      # Normalize multiple spaces/tabs
        text = text.strip()
        
        return text
    
    def extract_text_from_url(self, url):
        """Extract COMPLETE text from job posting URL"""
        try:
            print(f"🌐 Extracting content from URL: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Handle encoding properly
            if response.encoding is None:
                response.encoding = 'utf-8'
            
            # Convert response content to string for BeautifulSoup
            if hasattr(response, 'text'):
                html_content = response.text
            else:
                # Fallback: decode bytes
                html_content = response.content.decode('utf-8', errors='ignore')
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
                if element:
                    element.decompose()
            
            # Try to find main content areas (common job posting selectors)
            content_selectors = [
                '[class*="job-description"]',
                '[class*="description"]',
                '[class*="content"]',
                '[class*="posting"]',
                '.description',
                '.job-description',
                '.content',
                '#content',
                'main',
                'article',
                '[role="main"]'
            ]
            
            main_content = None
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    # Find the element with the most text content
                    for element in elements:
                        if element:
                            element_text = element.get_text(strip=True)
                            if element_text and len(element_text) > 200:  # Reasonable minimum for job description
                                main_content = element
                                print(f"✅ Found content with selector: {selector}")
                                break
                if main_content:
                    break
            
            # If no specific content area found, use the whole body but clean it
            if not main_content:
                main_content = soup.find('body') or soup
                print("ℹ️ Using full body content")
            
            # Get text and clean it
            if main_content:
                text = main_content.get_text()
            else:
                text = soup.get_text()
                
            lines = (line.strip() for line in text.splitlines() if line.strip())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Limit size but ensure we have substantial content
            if len(text) > 10000:
                print(f"⚠️ Content truncated from {len(text)} to 10000 characters")
                text = text[:10000]
            
            if len(text) < 100:
                print("❌ Extracted content seems too short")
                return None
            
            print(f"✅ Successfully extracted {len(text)} characters from URL")
            return text
            
        except Exception as e:
            print(f"❌ Error extracting from URL: {e}")
            return None

    def verify_extraction_completeness(self, text, source_type):
        """Verify that text extraction captured substantial content"""
        if not text:
            return False
        
        min_lengths = {
            'cv': 100,      # CV should have at least 100 characters
            'job': 200      # Job description should have at least 200 characters
        }
        
        min_length = min_lengths.get(source_type, 100)
        
        if len(text) < min_length:
            print(f"❌ {source_type.upper()} extraction failed: only {len(text)} characters (minimum: {min_length})")
            return False
        
        # Check if text has reasonable word count
        words = text.split()
        if len(words) < (min_length // 5):  # Rough word count check
            print(f"❌ {source_type.upper()} extraction suspicious: only {len(words)} words")
            return False
        
        print(f"✅ {source_type.upper()} extraction verified: {len(text)} characters, {len(words)} words")
        return True