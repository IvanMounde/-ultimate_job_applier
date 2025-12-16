# improved_document_generator.py - COMPLETE VERSION WITH FULL STYLING SUPPORT
# ----------------------------------------------------------------------------
# UPDATED WITH CV FORMAT TRANSFORMER STYLING AND SMART HEADING LOGIC
# INCLUDES ALL CUSTOMIZATION FEATURES FROM THE FRONTEND
# ----------------------------------------------------------------------------

import os
import re
from datetime import datetime
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from typing import Literal, Union, Dict, Optional, Tuple
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


class ImprovedDocumentGenerator:
    """Generate professional CV and Cover Letter in both PDF and DOCX formats with full styling support"""
    
    # Color palette mapping for frontend colors
    COLOR_PALETTE = {
        'BFBFBF': RGBColor(191, 191, 191),  # Light Gray (Default)
        'D4EDFF': RGBColor(212, 237, 255),  # Light Blue
        'FFE5D4': RGBColor(255, 229, 212),  # Light Peach
        'D4FFE5': RGBColor(212, 255, 229),  # Light Green
        'FFD4E5': RGBColor(255, 212, 229),  # Light Pink
        'FFFACD': RGBColor(255, 250, 205),  # Light Yellow
        'E5D4FF': RGBColor(229, 212, 255),  # Light Purple
    }
    
    # Font mapping for frontend
    FONT_MAPPING = {
        'Calibri': 'Calibri',
        'Arial': 'Arial',
        'Times New Roman': 'Times New Roman',
        'Georgia': 'Georgia',
        'Verdana': 'Verdana',
        'Tahoma': 'Tahoma',
    }
    
    def __init__(self, highlight_color: str = 'BFBFBF', 
                 font_family: str = 'Calibri',
                 base_font_size: float = 10.0):
        """
        Initialize document generator with customization options
        
        Args:
            highlight_color: Hex color for section highlights (without #)
            font_family: Font family for documents
            base_font_size: Base font size in points
        """
        self.highlight_color = highlight_color.upper()
        self.font_family = self.FONT_MAPPING.get(font_family, 'Calibri')
        self.base_font_size = float(base_font_size)
        
        # Initialize PDF styles with flag to prevent reinitialization
        self.pdf_styles_initialized = False
        self.styles = getSampleStyleSheet()
        
        print(f"🎨 Document Generator initialized with:")
        print(f"   • Highlight Color: #{self.highlight_color}")
        print(f"   • Font Family: {self.font_family}")
        print(f"   • Base Font Size: {self.base_font_size}pt")
    
    # ==================== CUSTOMIZATION SETTERS ====================
    
    def set_customization(self, highlight_color: Optional[str] = None, 
                          font_family: Optional[str] = None,
                          base_font_size: Optional[float] = None) -> None:
        """Update customization settings dynamically"""
        if highlight_color:
            self.highlight_color = highlight_color.upper()
        if font_family:
            self.font_family = self.FONT_MAPPING.get(font_family, 'Calibri')
        if base_font_size is not None:
            self.base_font_size = float(base_font_size)
        
        # Update PDF styles (will handle reinitialization gracefully)
        self._setup_pdf_styles()
    
    # ==================== CV FORMAT TRANSFORMER HELPER METHODS ====================
    
    def add_paragraph_shading(self, paragraph, fill_color: Optional[str] = None) -> None:
        """
        Add shading/background color to a paragraph
        
        Args:
            paragraph: docx paragraph object
            fill_color: hex color string without # (e.g., 'BFBFBF' for light blue)
                      If None, uses the instance highlight_color
        """
        if fill_color is None:
            fill_color = self.highlight_color
        
        pPr = paragraph._element.get_or_add_pPr()
        shading_elm = OxmlElement('w:shd')
        shading_elm.set(qn('w:fill'), fill_color.upper())
        shading_elm.set(qn('w:val'), 'clear')
        shading_elm.set(qn('w:color'), 'auto')
        pPr.append(shading_elm)
    
    def set_paragraph_spacing(self, paragraph, before: float = 0, after: float = 0, 
                              line_spacing: float = 1.0) -> None:
        """
        Set spacing before and after paragraph, and line spacing
        
        Args:
            paragraph: docx paragraph object
            before: Space before in points
            after: Space after in points
            line_spacing: Line spacing multiplier
        """
        paragraph_format = paragraph.paragraph_format
        paragraph_format.space_before = Pt(before)
        paragraph_format.space_after = Pt(after)
        paragraph_format.line_spacing = line_spacing
    
    def add_document_border(self, doc, border_size: str = '4', border_color: str = '000000') -> None:
        """
        Add a thin border around the entire document page
        
        Args:
            doc: docx Document object
            border_size: Border thickness in eighths of a point
            border_color: Hex color without #
        """
        for section in doc.sections:
            sectPr = section._sectPr
            pgBorders = OxmlElement('w:pgBorders')
            pgBorders.set(qn('w:offsetFrom'), 'page')
            
            for border_name in ['top', 'bottom', 'left', 'right']:
                border = OxmlElement(f'w:{border_name}')
                border.set(qn('w:val'), 'single')
                border.set(qn('w:sz'), border_size)
                border.set(qn('w:space'), '24')
                border.set(qn('w:color'), border_color)
                pgBorders.append(border)
            
            # Remove existing borders if any
            existing_borders = sectPr.findall(qn('w:pgBorders'))
            for border in existing_borders:
                sectPr.remove(border)
            
            sectPr.append(pgBorders)
    
    def create_page_number_element(self):
        """
        Create the XML elements for a page number field
        Returns a complete run element with page number field
        """
        run = OxmlElement('w:r')
        
        # Add "Page " text
        t1 = OxmlElement('w:t')
        t1.set(qn('xml:space'), 'preserve')
        t1.text = 'Page '
        run.append(t1)
        
        # Add page number field
        fldChar1 = OxmlElement('w:fldChar')
        fldChar1.set(qn('w:fldCharType'), 'begin')
        run.append(fldChar1)
        
        instrText = OxmlElement('w:instrText')
        instrText.set(qn('xml:space'), 'preserve')
        instrText.text = 'PAGE'
        run.append(instrText)
        
        fldChar2 = OxmlElement('w:fldChar')
        fldChar2.set(qn('w:fldCharType'), 'end')
        run.append(fldChar2)
        
        return run
    
    def clear_footer_completely(self, footer) -> None:
        """Completely clear all content from a footer"""
        footer_element = footer._element
        for child in list(footer_element):
            footer_element.remove(child)
    
    def add_page_number_to_footer(self, footer, font_size: int = 10) -> None:
        """
        Add page number to a footer (left aligned) with a faint line separator above
        
        Args:
            footer: docx footer object
            font_size: Font size in points (integer)
        """
        self.clear_footer_completely(footer)
        
        # Add a paragraph with a top border (faint line)
        para = footer.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        # Add a very faint top border to the paragraph
        pPr = para._element.get_or_add_pPr()
        pBdr = OxmlElement('w:pBdr')
        
        top_border = OxmlElement('w:top')
        top_border.set(qn('w:val'), 'single')
        top_border.set(qn('w:sz'), '4')  # Very thin line (0.5pt)
        top_border.set(qn('w:space'), '1')
        top_border.set(qn('w:color'), 'D3D3D3')  # Light gray color
        
        pBdr.append(top_border)
        pPr.append(pBdr)
        
        p_element = para._element
        
        # Create and add the page number run
        page_num_run = self.create_page_number_element()
        
        # Add run properties for font size and family
        rPr = OxmlElement('w:rPr')
        
        # Font size - convert to half-points (Word uses half-points)
        sz = OxmlElement('w:sz')
        sz.set(qn('w:val'), str(int(font_size * 2)))  # Convert to integer
        rPr.append(sz)
        
        # Font family
        rFonts = OxmlElement('w:rFonts')
        rFonts.set(qn('w:ascii'), self.font_family)
        rFonts.set(qn('w:hAnsi'), self.font_family)
        rPr.append(rFonts)
        
        page_num_run.insert(0, rPr)
        p_element.append(page_num_run)
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text by removing special characters, colons, underscores, etc.
        
        Args:
            text: Input text
            
        Returns:
            Normalized lowercase text
        """
        # Remove markdown formatting (**text**, __text__, etc.)
        text = re.sub(r'[*_]+', '', text)
        # Remove colons and extra spaces
        text = text.replace(':', '').strip()
        # Remove parentheses and their content
        text = re.sub(r'\([^)]*\)', '', text)
        # Remove extra spaces
        text = ' '.join(text.split())
        return text.lower()
    
    def is_main_section_heading(self, text: str) -> bool:
        """
        Determine if text is a MAIN section heading (top-level sections only)
        
        Args:
            text: Text to check
            
        Returns:
            True if text is a main section heading
        """
        text = text.strip()
        
        # Normalize the text
        normalized = self.normalize_text(text)
        
        # STRICT list of ONLY main section headings
        main_sections = [
            # Summary sections
            'professional summary', 'summary', 'career objective', 'objective',
            'personal profile', 'profile', 'executive summary',
            
            # Experience sections
            'work experience', 'professional experience', 'employment history',
            'experience', 'career history',
            
            # Education sections
            'education', 'academic qualifications', 'educational background',
            'qualifications', 'academic background',
            
            # Skills sections (main category only - not subcategories)
            'skills', 'core competencies', 'areas of expertise', 'expertise',
            'technical competencies', 'competencies',
            
            # Certification sections
            'certifications', 'professional certifications', 'certificates',
            'licenses and certifications',
            
            # Project sections
            'projects', 'selected projects', 'project experience',
            
            # Language sections
            'languages', 'language skills', 'language proficiency',
            
            # Reference sections
            'references', 'referees',
            
            # Achievement sections
            'key achievements', 'achievements', 'awards and honors', 'awards',
            
            # Other main sections
            'professional development', 'training', 'courses', 'conferences',
            'publications', 'research experience',
            
            # Contact sections (though usually handled separately)
            'contact information', 'personal information'
        ]
        
        # Check if normalized text exactly matches a main section
        if normalized in main_sections:
            return True
        
        # Additional check: if text is short and in ALL CAPS (common for main sections)
        if (text.isupper() and len(text.split()) <= 4 and len(text) < 40 and 
            not any(word in normalized for word in ['soft', 'hard', 'technical', 'professional', 'key'])):
            return True
        
        return False
    
    def is_sub_heading(self, text: str, previous_heading: Optional[str] = None) -> bool:
        """
        Determine if text is a sub-heading (should NOT be highlighted if it follows a main heading)
        
        Args:
            text: Text to check
            previous_heading: Previous heading text
            
        Returns:
            True if text is a sub-heading
        """
        text = text.strip()
        normalized = self.normalize_text(text)
        
        # Common sub-heading patterns
        sub_headings = [
            'soft skills', 'hard skills', 'technical skills', 'professional skills',
            'interpersonal skills', 'communication skills', 'leadership skills',
            'key achievements', 'major achievements', 'responsibilities',
            'roles and responsibilities', 'duties', 'key responsibilities',
            'professional experience', 'work experience', 'employment history',
            'education', 'academic background', 'professional development',
            'certifications', 'languages', 'references', 'projects',
            'tools and technologies', 'software skills', 'programming languages',
            'databases', 'frameworks', 'methodologies', 'operating systems'
        ]
        
        # If it's in the sub-headings list, it's definitely a sub-heading
        if normalized in sub_headings:
            return True
        
        # If previous heading was "Skills" and this contains "skills", it's a sub-heading
        if previous_heading and 'skill' in self.normalize_text(previous_heading):
            if 'skill' in normalized:
                return True
        
        # If previous heading was "Experience" and this contains "experience", it's a sub-heading
        if previous_heading and 'experience' in self.normalize_text(previous_heading):
            if 'experience' in normalized:
                return True
        
        # If previous heading was "Education" and this contains "education", it's a sub-heading
        if previous_heading and 'education' in self.normalize_text(previous_heading):
            if 'education' in normalized:
                return True
        
        return False
    
    def is_personal_info(self, text: str) -> bool:
        """
        Determine if text contains personal information (name, contact details)
        that should be centered at the top of the CV
        
        Args:
            text: Text to check
            
        Returns:
            True if text contains personal information
        """
        text = text.strip().lower()
        
        # Check if contains email
        if '@' in text and '.' in text:
            return True
        
        # Check if contains phone number patterns
        if any(char in text for char in ['+', '(', ')']) and any(char.isdigit() for char in text):
            return True
        
        # Check if contains common contact keywords
        contact_keywords = ['email:', 'phone:', 'tel:', 'mobile:', 'address:', 'linkedin', 'location:', 'www.']
        if any(keyword in text for keyword in contact_keywords):
            return True
        
        return False
    
    # ==================== PDF STYLES SETUP ====================
    
    def _setup_pdf_styles(self) -> None:
        """Setup custom PDF styles with current font settings"""
        try:
            # If styles are already initialized, remove custom styles before re-adding
            if self.pdf_styles_initialized:
                print("⚠️ PDF styles already initialized, updating with new settings...")
                # Remove existing custom styles to avoid duplicate key errors
                custom_style_names = ['CVName', 'CVContact', 'CVSection', 'CVSubSection', 
                                     'CVContent', 'CVBullet', 'CoverAddress', 'CoverBody']
                
                for style_name in custom_style_names:
                    if style_name in self.styles:
                        del self.styles.byName[style_name]
            
            # Calculate font sizes based on base font size
            name_size = int(self.base_font_size + 6)
            section_size = int(self.base_font_size + 2)
            content_size = int(self.base_font_size)
            
            # Get appropriate font names for ReportLab
            font_name = self._get_reportlab_font_name(self.font_family)
            
            # Create new styles - ReportLab will handle duplicates by overwriting
            # Note: We use try-except for each style to be extra safe
            try:
                self.styles.add(ParagraphStyle(
                    name='CVName',
                    parent=self.styles['Heading1'],
                    fontSize=name_size,
                    spaceAfter=4,
                    textColor=colors.black,
                    alignment=TA_CENTER,
                    fontName=font_name + '-Bold'
                ))
            except Exception as e:
                print(f"⚠️ Warning creating CVName style: {e}")
                # Update existing style
                if 'CVName' in self.styles:
                    self.styles['CVName'].fontSize = name_size
                    self.styles['CVName'].fontName = font_name + '-Bold'
            
            try:
                self.styles.add(ParagraphStyle(
                    name='CVContact',
                    parent=self.styles['Normal'],
                    fontSize=content_size - 1,
                    spaceAfter=8,
                    textColor=colors.HexColor('#333333'),
                    alignment=TA_CENTER,
                    fontName=font_name
                ))
            except Exception as e:
                print(f"⚠️ Warning creating CVContact style: {e}")
                if 'CVContact' in self.styles:
                    self.styles['CVContact'].fontSize = content_size - 1
                    self.styles['CVContact'].fontName = font_name
            
            try:
                self.styles.add(ParagraphStyle(
                    name='CVSection',
                    parent=self.styles['Heading2'],
                    fontSize=section_size,
                    spaceAfter=6,
                    spaceBefore=10,
                    textColor=colors.black,
                    alignment=TA_CENTER,
                    fontName=font_name + '-Bold'
                ))
            except Exception as e:
                print(f"⚠️ Warning creating CVSection style: {e}")
                if 'CVSection' in self.styles:
                    self.styles['CVSection'].fontSize = section_size
                    self.styles['CVSection'].fontName = font_name + '-Bold'
            
            try:
                self.styles.add(ParagraphStyle(
                    name='CVSubSection',
                    parent=self.styles['Normal'],
                    fontSize=content_size,
                    spaceAfter=4,
                    spaceBefore=6,
                    textColor=colors.black,
                    fontName=font_name + '-Bold'
                ))
            except Exception as e:
                print(f"⚠️ Warning creating CVSubSection style: {e}")
                if 'CVSubSection' in self.styles:
                    self.styles['CVSubSection'].fontSize = content_size
                    self.styles['CVSubSection'].fontName = font_name + '-Bold'
            
            try:
                self.styles.add(ParagraphStyle(
                    name='CVContent',
                    parent=self.styles['Normal'],
                    fontSize=content_size,
                    spaceAfter=4,
                    leading=content_size * 1.4,
                    alignment=TA_JUSTIFY,
                    fontName=font_name
                ))
            except Exception as e:
                print(f"⚠️ Warning creating CVContent style: {e}")
                if 'CVContent' in self.styles:
                    self.styles['CVContent'].fontSize = content_size
                    self.styles['CVContent'].leading = content_size * 1.4
                    self.styles['CVContent'].fontName = font_name
            
            try:
                self.styles.add(ParagraphStyle(
                    name='CVBullet',
                    parent=self.styles['Normal'],
                    fontSize=content_size,
                    spaceAfter=3,
                    leading=content_size * 1.4,
                    leftIndent=20,
                    bulletIndent=10,
                    fontName=font_name
                ))
            except Exception as e:
                print(f"⚠️ Warning creating CVBullet style: {e}")
                if 'CVBullet' in self.styles:
                    self.styles['CVBullet'].fontSize = content_size
                    self.styles['CVBullet'].fontName = font_name
            
            try:
                self.styles.add(ParagraphStyle(
                    name='CoverAddress',
                    parent=self.styles['Normal'],
                    fontSize=content_size + 1,
                    spaceAfter=4,
                    fontName=font_name
                ))
            except Exception as e:
                print(f"⚠️ Warning creating CoverAddress style: {e}")
                if 'CoverAddress' in self.styles:
                    self.styles['CoverAddress'].fontSize = content_size + 1
                    self.styles['CoverAddress'].fontName = font_name
            
            try:
                self.styles.add(ParagraphStyle(
                    name='CoverBody',
                    parent=self.styles['Normal'],
                    fontSize=content_size + 1,
                    spaceAfter=12,
                    alignment=TA_JUSTIFY,
                    leading=(content_size + 1) * 1.5,
                    fontName=font_name
                ))
            except Exception as e:
                print(f"⚠️ Warning creating CoverBody style: {e}")
                if 'CoverBody' in self.styles:
                    self.styles['CoverBody'].fontSize = content_size + 1
                    self.styles['CoverBody'].leading = (content_size + 1) * 1.5
                    self.styles['CoverBody'].fontName = font_name
            
            self.pdf_styles_initialized = True
            print(f"✅ PDF styles updated successfully")
            
        except Exception as e:
            print(f"❌ Error setting up PDF styles: {e}")
            import traceback
            traceback.print_exc()
            # Ensure we always have a styles object
            if not self.styles:
                self.styles = getSampleStyleSheet()
    
    def _get_reportlab_font_name(self, font_family: str) -> str:
        """
        Map common font families to ReportLab font names
        
        Args:
            font_family: Common font family name
            
        Returns:
            ReportLab compatible font name
        """
        font_map = {
            'Calibri': 'Helvetica',
            'Arial': 'Helvetica',
            'Times New Roman': 'Times-Roman',
            'Georgia': 'Times-Roman',
            'Verdana': 'Helvetica',
            'Tahoma': 'Helvetica'
        }
        return font_map.get(font_family, 'Helvetica')
    
    # ==================== DOCUMENT EXTRACTION ====================
    
    def extract_documents_from_response(self, ai_response: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract CV and Cover Letter content from AI response
        
        Args:
            ai_response: Complete AI response string
            
        Returns:
            Tuple of (cv_content, cover_content)
        """
        if not ai_response:
            print("❌ No AI response provided")
            return None, None
        
        print(f"📝 Extracting documents from {len(ai_response)} characters...")
        
        cv_content: Optional[str] = None
        cover_content: Optional[str] = None
        
        # Try exact delimiters first
        cv_start = "===OPTIMIZED_CV_START==="
        cv_end = "===OPTIMIZED_CV_END==="
        cover_start = "===COVER_LETTER_START==="
        cover_end = "===COVER_LETTER_END==="
        
        # Extract CV
        cv_start_idx = ai_response.find(cv_start)
        cv_end_idx = ai_response.find(cv_end)
        if cv_start_idx != -1 and cv_end_idx != -1 and cv_start_idx < cv_end_idx:
            cv_content = ai_response[cv_start_idx + len(cv_start):cv_end_idx].strip()
            print(f"✅ Extracted CV: {len(cv_content)} characters")
        else:
            print("⚠️ CV delimiters not found, trying alternative extraction...")
            cv_content = self._extract_cv_alternative(ai_response)
        
        # Extract Cover Letter
        cover_start_idx = ai_response.find(cover_start)
        cover_end_idx = ai_response.find(cover_end)
        if cover_start_idx != -1 and cover_end_idx != -1 and cover_start_idx < cover_end_idx:
            cover_content = ai_response[cover_start_idx + len(cover_start):cover_end_idx].strip()
            print(f"✅ Extracted Cover Letter: {len(cover_content)} characters")
        else:
            print("⚠️ Cover Letter delimiters not found, trying alternative extraction...")
            cover_content = self._extract_cover_alternative(ai_response)
        
        # Replace date placeholders
        if cv_content:
            cv_content = self._replace_date_placeholders(cv_content)
        if cover_content:
            cover_content = self._replace_date_placeholders(cover_content)
        
        return cv_content, cover_content
    
    def _extract_cv_alternative(self, text: str) -> Optional[str]:
        """Alternative CV extraction using patterns"""
        patterns = [
            r'(PROFESSIONAL SUMMARY.*?(?=COVER LETTER|===COVER_LETTER|$))',
            r'(CONTACT.*?EDUCATION.*?SKILLS)',
            r'([A-Z][a-z]+ [A-Z][a-z]+\s*\n.*?PROFESSIONAL SUMMARY.*?SKILLS)',
            r'([A-Z\s]+\n.*?phone.*?PROFESSIONAL SUMMARY.*?(?=COVER LETTER|$))',
            r'(\*\*[A-Z\s]+\*\*\n.*?PROFESSIONAL SUMMARY.*?(?=COVER LETTER|$))'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match and len(match.group(1)) > 300:
                print(f"✅ CV extracted using alternative pattern: {len(match.group(1))} chars")
                return match.group(1).strip()
        
        print("❌ No CV pattern matched")
        return None
    
    def _extract_cover_alternative(self, text: str) -> Optional[str]:
        """Alternative Cover Letter extraction using patterns"""
        patterns = [
            r'(Dear Hiring Manager.*?Sincerely,.*?[A-Z][a-z]+ [A-Z][a-z]+)',
            r'(\[?(?:Current )?Date\]?.*?Dear.*?Sincerely.*)',
            r'([A-Z][a-z]+ [A-Z][a-z]+\n.*?Dear.*?(?:Sincerely|Best Regards|Yours Faithfully).*?[A-Z][a-z]+ [A-Z][a-z]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match and len(match.group(1)) > 200:
                print(f"✅ Cover Letter extracted using alternative pattern: {len(match.group(1))} chars")
                return match.group(1).strip()
        
        print("❌ No Cover Letter pattern matched")
        return None
    
    def _replace_date_placeholders(self, text: str) -> str:
        """Replace date placeholders with current date"""
        current_date = datetime.now().strftime("%B %d, %Y")
        patterns = [
            r'\[DATE\]', r'\[CURRENT[ _]DATE\]', r'\[Current Date\]', r'\[Today\'s Date\]',
            r'\{DATE\}', r'\{CURRENT_DATE\}', r'DATE:', r'Date:'
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, current_date, text, flags=re.IGNORECASE)
        
        return text
    
    # ==================== HELPER METHODS ====================
    
    def _is_contact_line(self, line: str) -> bool:
        """Check if line contains contact information"""
        line_lower = line.lower()
        return any(ind in line_lower for ind in ['phone', 'tel:', 'email:', '@', 'linkedin', 'www.', 'github'])
    
    def _is_company_line(self, line: str) -> bool:
        """Check if line is a company/organization name"""
        return bool(re.match(r'^[A-Z\s&,\-]+\s*(\(.*\))?$', line.strip()))
    
    def _is_date_range_line(self, line: str) -> bool:
        """Check if line is a date range"""
        patterns = [
            r'\d{2}/\d{4}\s*--\s*\d{2}/\d{4}',
            r'\d{2}/\d{4}\s*--\s*Present',
            r'\d{4}\s*-\s*\d{4}',
            r'\d{4}\s*-\s*Present',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\s*-\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\s*-\s*Present'
        ]
        return any(re.search(p, line, re.IGNORECASE) for p in patterns)
    
    def _is_underlined_subsection(self, line: str) -> bool:
        """Check if line should be an underlined subsection"""
        line_lower = line.lower()
        return any(s in line_lower for s in ['key achievements', 'other positions held', 'areas of expertise'])
    
    def _is_bullet_point(self, line: str) -> bool:
        """Check if line is a bullet point"""
        stripped = line.strip()
        return stripped.startswith('•') or stripped.startswith('-') or stripped.startswith('*') or stripped.startswith('·')
    
    def _normalize_bullet_text(self, line: str) -> str:
        """Extract and format bullet point text"""
        # Remove bullet character and leading spaces
        bullet_text = re.sub(r'^[•\-*\·]\s*', '', line.strip()).strip()
        
        # Bold metrics (numbers with + or %)
        bullet_text = self._bold_metrics(bullet_text)
        
        # Convert ALL CAPS bullets to sentence case, but preserve bold formatting
        plain_text = re.sub(r'<.*?>', '', bullet_text)
        if plain_text.isupper() and len(plain_text) > 5:
            parts = re.split(r'(<b>.*?</b>)', bullet_text)
            result = []
            for part in parts:
                if part.startswith('<b>') and part.endswith('</b>'):
                    result.append(part)  # Keep bold content as-is
                elif part:
                    result.append(part.capitalize())  # Convert to sentence case
            bullet_text = ''.join(result)
        
        return bullet_text
    
    def _bold_metrics(self, text: str) -> str:
        """Bold only numbers with + or %: 15+, 30%"""
        # Find and bold metrics like 15+, 30%
        text = re.sub(r'(\d+[\+%])', r'<b>\1</b>', text)
        
        # Also bold percentage increases/decreases like "increased by 30%"
        text = re.sub(r'(by\s+)(\d+%)', r'\1<b>\2</b>', text)
        
        return text
    
    # ==================== ENHANCED DOCX GENERATION WITH CUSTOM STYLING ====================
    
    def generate_cv_docx(self, cv_content: str, output_path: str) -> bool:
        """
        Generate a professionally formatted CV DOCX with full styling support
        
        Args:
            cv_content: CV text content
            output_path: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"📄 Generating CV DOCX with custom styling: {len(cv_content)} characters")
            print(f"   • Highlight Color: #{self.highlight_color}")
            print(f"   • Font Family: {self.font_family}")
            print(f"   • Font Size: {self.base_font_size}pt")
            
            # Create document
            doc = Document()
            
            # Set document margins (professional formatting)
            for section in doc.sections:
                section.top_margin = Inches(0.5)
                section.bottom_margin = Inches(0.5)
                section.left_margin = Inches(0.7)
                section.right_margin = Inches(0.7)
            
            # Add thin page border
            self.add_document_border(doc)
            
            # Add page numbers to footers - convert float to int
            footer_font_size = int(self.base_font_size - 1)
            print("📌 Adding page numbers...")
            for section in doc.sections:
                section.different_first_page_header_footer = False
                self.clear_footer_completely(section.footer)
                self.add_page_number_to_footer(section.footer, font_size=footer_font_size)
            
            # Parse CV content
            lines = cv_content.split('\n')
            name_found = False
            last_main_heading: Optional[str] = None
            
            # First pass: analyze all lines to understand structure
            analyzed_lines = []
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                
                # Clean the line for processing
                line_clean = line_stripped.replace('**', '').replace('###', '').replace('##', '')
                
                # Determine line type
                is_main_heading = self.is_main_section_heading(line_clean)
                is_personal_info = self.is_personal_info(line_clean)
                is_bullet = self._is_bullet_point(line_stripped)
                is_contact = self._is_contact_line(line_clean)
                
                # Check if this is a sub-heading of the last main heading
                is_sub_heading = False
                if last_main_heading and not is_main_heading:
                    is_sub_heading = self.is_sub_heading(line_clean, last_main_heading)
                
                analyzed_lines.append({
                    'original': line_stripped,
                    'clean': line_clean,
                    'index': i,
                    'is_main_heading': is_main_heading,
                    'is_sub_heading': is_sub_heading,
                    'is_personal_info': is_personal_info,
                    'is_bullet': is_bullet,
                    'is_contact': is_contact,
                    'is_company': self._is_company_line(line_clean),
                    'is_date_range': self._is_date_range_line(line_clean),
                    'is_underlined': self._is_underlined_subsection(line_clean),
                })
                
                # Update last main heading
                if is_main_heading:
                    last_main_heading = line_clean
            
            # Second pass: apply formatting with custom styling
            for i, line_data in enumerate(analyzed_lines):
                line_stripped = line_data['original']
                line_clean = line_data['clean']
                
                # 1. NAME - First non-empty line is usually the name
                if not name_found and not line_data['is_personal_info'] and not line_data['is_bullet']:
                    p = doc.add_paragraph()
                    
                    # Apply font family and size
                    run = p.add_run(line_clean)
                    run.font.size = Pt(int(self.base_font_size + 6))  # Larger for name
                    run.font.name = self.font_family
                    run.bold = True
                    
                    # Center align
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.space_after = Pt(4)
                    
                    name_found = True
                    print(f"👤 Name detected: {line_clean}")
                    continue
                
                # 2. CONTACT INFORMATION - Center align personal info
                elif line_data['is_personal_info'] or line_data['is_contact']:
                    p = doc.add_paragraph(line_clean)
                    p.runs[0].font.size = Pt(int(self.base_font_size - 1))  # Slightly smaller
                    p.runs[0].font.name = self.font_family
                    
                    # Center align
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.space_after = Pt(4)
                    continue
                
                # 3. MAIN SECTION HEADERS - Apply custom styling
                elif line_data['is_main_heading'] and not line_data['is_sub_heading']:
                    # Check if this is a consecutive heading
                    is_consecutive_heading = False
                    if i > 0:
                        prev_line = analyzed_lines[i-1]
                        if prev_line['is_main_heading'] or prev_line['is_sub_heading']:
                            is_consecutive_heading = True
                    
                    # Only highlight if it's not a consecutive heading
                    if not is_consecutive_heading:
                        p = doc.add_paragraph()
                        
                        # Add the text
                        run = p.add_run(line_clean.upper())
                        run.font.size = Pt(int(self.base_font_size + 2))  # Larger for headings
                        run.bold = True
                        run.font.name = self.font_family
                        
                        # Center the heading
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        
                        # Set professional spacing
                        self.set_paragraph_spacing(p, before=12, after=8, line_spacing=1.0)
                        
                        # Add custom colored shading
                        self.add_paragraph_shading(p, self.highlight_color)
                        
                        print(f"✅ Highlighted MAIN section: {line_clean}")
                    else:
                        # This is a consecutive heading - format it as bold but not highlighted
                        p = doc.add_paragraph()
                        run = p.add_run(line_clean)
                        run.font.size = Pt(int(self.base_font_size + 1))
                        run.bold = True
                        run.font.name = self.font_family
                        p.space_before = Pt(8)
                        p.space_after = Pt(4)
                        print(f"⚠️ Skipped highlighting (consecutive heading): {line_clean}")
                    
                    continue
                
                # 4. SUB-HEADINGS - Format as bold but NOT highlighted
                elif line_data['is_sub_heading']:
                    p = doc.add_paragraph()
                    run = p.add_run(line_clean)
                    run.font.size = Pt(int(self.base_font_size + 1))
                    run.bold = True
                    run.font.name = self.font_family
                    p.space_before = Pt(8)
                    p.space_after = Pt(4)
                    print(f"📝 Formatted as SUB-heading: {line_clean}")
                    continue
                
                # 5. UNDERLINED SUBSECTIONS
                elif line_data['is_underlined']:
                    p = doc.add_paragraph()
                    run = p.add_run(line_clean)
                    run.font.size = Pt(int(self.base_font_size + 1))
                    run.bold = True
                    run.underline = True
                    run.font.name = self.font_family
                    p.space_before = Pt(10)
                    p.space_after = Pt(6)
                    continue
                
                # 6. BULLET POINTS
                elif line_data['is_bullet']:
                    bullet_text = self._normalize_bullet_text(line_stripped)
                    
                    p = doc.add_paragraph(style='List Bullet')
                    p.paragraph_format.left_indent = Inches(0.25)
                    p.paragraph_format.space_after = Pt(4)
                    
                    # Parse bold formatting
                    parts = re.split(r'(<b>.*?</b>)', bullet_text)
                    for part in parts:
                        if not part:
                            continue
                        if part.startswith('<b>') and part.endswith('</b>'):
                            text = part[3:-4]
                            run = p.add_run(text)
                            run.bold = True
                        else:
                            run = p.add_run(part)
                            run.bold = False
                        run.font.size = Pt(int(self.base_font_size))
                        run.font.name = self.font_family
                    continue
                
                # 7. COMPANY LINES
                elif line_data['is_company']:
                    p = doc.add_paragraph()
                    match = re.match(r'^([^(]+)\s*(\(.*\))?', line_clean)
                    if match:
                        company_name = match.group(1).strip()
                        description = match.group(2) if match.group(2) else ''
                        run1 = p.add_run(company_name)
                        run1.font.size = Pt(int(self.base_font_size + 1))
                        run1.bold = True
                        run1.font.name = self.font_family
                        if description:
                            run2 = p.add_run(' ' + description)
                            run2.font.size = Pt(int(self.base_font_size - 1))
                            run2.italic = True
                            run2.font.name = self.font_family
                    p.space_before = Pt(10)
                    p.space_after = Pt(4)
                    continue
                
                # 8. DATE RANGE LINES
                elif line_data['is_date_range']:
                    p = doc.add_paragraph()
                    run = p.add_run(line_clean)
                    run.font.size = Pt(int(self.base_font_size))
                    run.bold = True
                    run.font.name = self.font_family
                    p.space_after = Pt(6)
                    continue
                
                # 9. DEFAULT PARAGRAPH (Regular text)
                else:
                    p = doc.add_paragraph(line_clean)
                    p.runs[0].font.size = Pt(int(self.base_font_size))
                    p.runs[0].font.name = self.font_family
                    
                    # Justify longer paragraphs for professional look
                    if len(line_clean) > 100:
                        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    
                    p.space_after = Pt(6)
            
            # Save the document
            doc.save(output_path)
            print(f"✅ CV DOCX with custom styling saved: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating CV DOCX: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_cover_letter_docx(self, cover_content: str, output_path: str) -> bool:
        """
        Generate a professionally formatted Cover Letter DOCX with custom styling
        
        Args:
            cover_content: Cover letter text content
            output_path: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"📝 Generating Cover Letter DOCX: {len(cover_content)} characters")
            
            doc = Document()
            
            # Set cover letter margins (more generous than CV)
            for section in doc.sections:
                section.top_margin = Inches(1)
                section.bottom_margin = Inches(1)
                section.left_margin = Inches(1)
                section.right_margin = Inches(1)
            
            lines = cover_content.split('\n')
            in_signature_area = False
            in_header = True
            
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                
                line_clean = line_stripped.replace('**', '')
                
                # Header section (address, date, etc.)
                if in_header and i < 6 and 'Dear' not in line_clean:
                    p = doc.add_paragraph(line_clean)
                    p.runs[0].font.size = Pt(int(self.base_font_size + 1))
                    p.runs[0].font.name = self.font_family
                    p.space_after = Pt(4)
                    continue
                
                # Date line
                elif re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}', line_clean):
                    in_header = False
                    p = doc.add_paragraph()
                    p.add_run('\n')
                    p = doc.add_paragraph(line_clean)
                    p.runs[0].font.size = Pt(int(self.base_font_size + 1))
                    p.runs[0].font.name = self.font_family
                    p.space_after = Pt(12)
                    continue
                
                # Other header lines
                elif in_header or (i < 15 and 'Dear' not in line_clean):
                    in_header = False
                    p = doc.add_paragraph(line_clean)
                    p.runs[0].font.size = Pt(int(self.base_font_size + 1))
                    p.runs[0].font.name = self.font_family
                    p.space_after = Pt(4)
                    continue
                
                # Salutation (Dear...)
                elif 'Dear' in line_clean:
                    p = doc.add_paragraph()
                    p.add_run('\n')
                    p = doc.add_paragraph(line_clean)
                    p.runs[0].font.size = Pt(int(self.base_font_size + 1))
                    p.runs[0].font.name = self.font_family
                    p.space_after = Pt(12)
                    in_header = False
                    continue
                
                # Closing (Sincerely, etc.)
                elif line_clean.upper() in ['SINCERELY,', 'BEST REGARDS,', 'YOURS FAITHFULLY,', 'RESPECTFULLY,']:
                    in_signature_area = True
                    doc.add_paragraph()
                    p = doc.add_paragraph(line_clean)
                    p.runs[0].font.size = Pt(int(self.base_font_size + 1))
                    p.runs[0].font.name = self.font_family
                    p.space_after = Pt(36)
                    continue
                
                # Signature area (name, title, etc.)
                elif in_signature_area:
                    p = doc.add_paragraph(line_clean)
                    p.runs[0].font.size = Pt(int(self.base_font_size + 1))
                    p.runs[0].bold = True
                    p.runs[0].font.name = self.font_family
                    continue
                
                # Body text
                else:
                    p = doc.add_paragraph(line_clean)
                    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    p.runs[0].font.size = Pt(int(self.base_font_size + 1))
                    p.runs[0].font.name = self.font_family
                    p.space_after = Pt(12)
            
            doc.save(output_path)
            print(f"✅ Cover Letter DOCX saved: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating Cover Letter DOCX: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ==================== PDF GENERATION WITH CUSTOM STYLING ====================
    
    def generate_cv_pdf(self, cv_content: str, output_path: str) -> bool:
        """
        Generate a professionally formatted CV PDF with custom styling
        
        Args:
            cv_content: CV text content
            output_path: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"📄 Generating CV PDF with custom styling: {len(cv_content)} characters")
            
            # Calculate PDF highlight color
            highlight_rgb = self.COLOR_PALETTE.get(self.highlight_color, colors.HexColor('#BFBFBF'))
            
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch,
                leftMargin=0.75*inch,
                rightMargin=0.75*inch
            )
            
            story = []
            lines = cv_content.split('\n')
            current_section: Optional[str] = None
            
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                
                line_clean = line_stripped.replace('**', '').replace('###', '').replace('##', '')
                
                # Check for bullet FIRST
                if self._is_bullet_point(line_stripped):
                    bullet_text = self._normalize_bullet_text(line_stripped)
                    story.append(Paragraph(f"• {bullet_text}", self.styles['CVBullet']))
                    continue
                
                # Name (first line or all caps short line)
                if i == 0 or (line_clean.isupper() and len(line_clean.split()) <= 3 and not current_section):
                    story.append(Paragraph(line_clean, self.styles['CVName']))
                    continue
                
                # Contact information
                elif self._is_contact_line(line_clean):
                    story.append(Paragraph(line_clean, self.styles['CVContact']))
                    continue
                
                # Main section headings
                elif self.is_main_section_heading(line_clean):
                    story.append(Spacer(1, 10))
                    
                    # Create a styled paragraph
                    section_text = f"<para align='center'><font name='{self._get_reportlab_font_name(self.font_family)}-Bold' size='{int(self.base_font_size + 2)}'>{line_clean.upper()}</font></para>"
                    story.append(Paragraph(section_text, self.styles['CVSection']))
                    current_section = line_clean
                    continue
                
                # Underlined subsections
                elif self._is_underlined_subsection(line_clean):
                    story.append(Spacer(1, 6))
                    story.append(Paragraph(f"<b><u>{line_clean}</u></b>", self.styles['CVSubSection']))
                    continue
                
                # Company lines
                elif self._is_company_line(line_clean):
                    match = re.match(r'^([^(]+)\s*(\(.*\))?', line_clean)
                    if match:
                        company = match.group(1).strip()
                        desc = match.group(2) if match.group(2) else ''
                        formatted = f"<b>{company}</b> <i>{desc}</i>"
                        story.append(Spacer(1, 6))
                        story.append(Paragraph(formatted, self.styles['CVContent']))
                    continue
                
                # Date range lines
                elif self._is_date_range_line(line_clean):
                    story.append(Paragraph(f"<b>{line_clean}</b>", self.styles['CVContent']))
                    continue
                
                # Job titles (all caps or title case)
                elif re.match(r'^[A-Z][A-Za-z\s&,\-()]+$', line_clean) and len(line_clean) < 80:
                    story.append(Paragraph(f"<b>{line_clean}</b>", self.styles['CVContent']))
                    continue
                
                # Regular content
                else:
                    story.append(Paragraph(line_clean, self.styles['CVContent']))
            
            doc.build(story)
            print(f"✅ CV PDF with custom styling saved: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating CV PDF: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_cover_letter_pdf(self, cover_content: str, output_path: str) -> bool:
        """
        Generate a professionally formatted Cover Letter PDF with custom styling
        
        Args:
            cover_content: Cover letter text content
            output_path: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"📝 Generating Cover Letter PDF: {len(cover_content)} characters")
            
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                topMargin=1*inch,
                bottomMargin=1*inch,
                leftMargin=1*inch,
                rightMargin=1*inch
            )
            
            story = []
            lines = cover_content.split('\n')
            in_signature_area = False
            in_header = True
            
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                
                line_clean = line_stripped.replace('**', '')
                
                if in_header and i < 6 and 'Dear' not in line_clean:
                    story.append(Paragraph(line_clean, self.styles['CoverAddress']))
                    continue
                
                elif re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}', line_clean):
                    in_header = False
                    story.append(Spacer(1, 12))
                    story.append(Paragraph(line_clean, self.styles['CoverAddress']))
                    story.append(Spacer(1, 12))
                    continue
                
                elif in_header or (i < 15 and 'Dear' not in line_clean):
                    in_header = False
                    story.append(Paragraph(line_clean, self.styles['CoverAddress']))
                    continue
                
                elif 'Dear' in line_clean:
                    story.append(Spacer(1, 12))
                    story.append(Paragraph(line_clean, self.styles['CoverAddress']))
                    story.append(Spacer(1, 12))
                    in_header = False
                    continue
                
                elif line_clean.upper() in ['SINCERELY,', 'BEST REGARDS,', 'YOURS FAITHFULLY,', 'RESPECTFULLY,']:
                    in_signature_area = True
                    story.append(Spacer(1, 24))
                    story.append(Paragraph(line_clean, self.styles['CoverAddress']))
                    story.append(Spacer(1, 36))
                    continue
                
                elif in_signature_area:
                    story.append(Paragraph(f"<b>{line_clean}</b>", self.styles['CoverAddress']))
                    continue
                
                else:
                    story.append(Paragraph(line_clean, self.styles['CoverBody']))
            
            doc.build(story)
            print(f"✅ Cover Letter PDF saved: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating Cover Letter PDF: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ==================== MERGED OUTPUT WITH CUSTOM STYLING ====================
    
    def generate_merged_output(self, cv_content: str, cover_content: str, 
                              output_path: str, format: str = 'pdf') -> bool:
        """
        Generate merged CV and Cover Letter in a single document
        
        Args:
            cv_content: CV text content
            cover_content: Cover letter text content
            output_path: Output file path
            format: Output format ('pdf' or 'docx')
            
        Returns:
            True if successful, False otherwise
        """
        if format not in ['pdf', 'docx']:
            print("❌ Merged format must be 'pdf' or 'docx'")
            return False
        
        print(f"📦 Generating merged {format.upper()}: {output_path}")
        
        try:
            if format == 'pdf':
                # Create merged PDF
                doc = SimpleDocTemplate(
                    output_path,
                    pagesize=letter,
                    topMargin=0.75*inch,
                    bottomMargin=0.75*inch,
                    leftMargin=0.75*inch,
                    rightMargin=0.75*inch
                )
                
                story = []
                
                # Add Cover Letter
                if cover_content:
                    for line in cover_content.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        clean = line.replace('**', '')
                        
                        if 'Dear' in clean:
                            story.append(Spacer(1, 12))
                            story.append(Paragraph(clean, self.styles['CoverAddress']))
                            story.append(Spacer(1, 12))
                        elif clean.upper() in ['SINCERELY,', 'BEST REGARDS,', 'YOURS FAITHFULLY,', 'RESPECTFULLY,']:
                            story.append(Spacer(1, 24))
                            story.append(Paragraph(clean, self.styles['CoverAddress']))
                            story.append(Spacer(1, 36))
                        elif clean.replace(' ', '').isupper() and len(clean) < 100:
                            story.append(Paragraph(clean, self.styles['CoverAddress']))
                        else:
                            story.append(Paragraph(clean, self.styles['CoverBody']))
                    
                    story.append(PageBreak())
                
                # Add CV
                if cv_content:
                    for i, line in enumerate(cv_content.split('\n')):
                        line = line.strip()
                        if not line:
                            continue
                        clean = line.replace('**', '').replace('###', '').replace('##', '')
                        
                        # Handle bullets FIRST
                        if self._is_bullet_point(line):
                            bullet = self._normalize_bullet_text(line)
                            story.append(Paragraph(f"• {bullet}", self.styles['CVBullet']))
                            continue
                        
                        if i == 0 or (clean.isupper() and len(clean.split()) <= 3):
                            story.append(Paragraph(clean, self.styles['CVName']))
                        elif self._is_contact_line(clean):
                            story.append(Paragraph(clean, self.styles['CVContact']))
                        elif self.is_main_section_heading(clean):
                            story.append(Spacer(1, 10))
                            story.append(Paragraph(f"<b>{clean.upper()}</b>", self.styles['CVSection']))
                        else:
                            story.append(Paragraph(clean, self.styles['CVContent']))
                
                doc.build(story)
                print(f"✅ Merged PDF with custom styling saved: {output_path}")
                
            else:  # DOCX
                # Create merged DOCX
                doc = Document()
                
                # Apply custom styling to merged document
                for section in doc.sections:
                    section.top_margin = Inches(0.5)
                    section.bottom_margin = Inches(0.5)
                    section.left_margin = Inches(0.7)
                    section.right_margin = Inches(0.7)
                
                # Add thin page border
                self.add_document_border(doc)
                
                # Add page numbers - convert float to int
                footer_font_size = int(self.base_font_size - 1)
                for section in doc.sections:
                    section.different_first_page_header_footer = False
                    self.clear_footer_completely(section.footer)
                    self.add_page_number_to_footer(section.footer, font_size=footer_font_size)
                
                # Add Cover Letter
                if cover_content:
                    in_header = True
                    for line in cover_content.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        clean = line.replace('**', '')
                        
                        if in_header and 'Dear' not in clean:
                            p = doc.add_paragraph(clean)
                            p.runs[0].font.size = Pt(int(self.base_font_size + 1))
                            p.runs[0].font.name = self.font_family
                        elif 'Dear' in clean:
                            doc.add_paragraph()
                            p = doc.add_paragraph(clean)
                            p.runs[0].font.size = Pt(int(self.base_font_size + 1))
                            p.runs[0].font.name = self.font_family
                            doc.add_paragraph()
                            in_header = False
                        elif clean.upper() in ['SINCERELY,', 'BEST REGARDS,', 'YOURS FAITHFULLY,', 'RESPECTFULLY,']:
                            doc.add_paragraph()
                            p = doc.add_paragraph(clean)
                            p.runs[0].font.size = Pt(int(self.base_font_size + 1))
                            p.runs[0].font.name = self.font_family
                            doc.add_paragraph()
                        elif clean.replace(' ', '').isupper():
                            p = doc.add_paragraph(clean)
                            p.runs[0].font.size = Pt(int(self.base_font_size + 1))
                            p.runs[0].bold = True
                            p.runs[0].font.name = self.font_family
                        else:
                            p = doc.add_paragraph(clean)
                            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                            p.runs[0].font.size = Pt(int(self.base_font_size + 1))
                            p.runs[0].font.name = self.font_family
                    
                    # Page Break
                    p = doc.add_paragraph()
                    run = p.add_run()
                    run.add_break(WD_BREAK.PAGE)
                
                # Add CV with custom styling
                if cv_content:
                    # Parse CV content for merged document
                    cv_lines = cv_content.split('\n')
                    analyzed_lines = []
                    last_main_heading: Optional[str] = None
                    
                    # Analyze CV lines
                    for i, line in enumerate(cv_lines):
                        line = line.strip()
                        if not line:
                            continue
                        clean = line.replace('**', '').replace('###', '').replace('##', '')
                        
                        is_main_heading = self.is_main_section_heading(clean)
                        is_sub_heading = False
                        if last_main_heading and not is_main_heading:
                            is_sub_heading = self.is_sub_heading(clean, last_main_heading)
                        
                        analyzed_lines.append({
                            'original': line,
                            'clean': clean,
                            'index': i,
                            'is_main_heading': is_main_heading,
                            'is_sub_heading': is_sub_heading,
                            'is_personal_info': self.is_personal_info(clean),
                            'is_bullet': self._is_bullet_point(line),
                            'is_contact': self._is_contact_line(clean),
                        })
                        
                        if is_main_heading:
                            last_main_heading = clean
                    
                    # Apply formatting with custom styling
                    name_found = False
                    for i, line_data in enumerate(analyzed_lines):
                        line = line_data['original']
                        clean = line_data['clean']
                        
                        # Handle bullets FIRST
                        if line_data['is_bullet']:
                            bullet = self._normalize_bullet_text(line)
                            p = doc.add_paragraph(style='List Bullet')
                            p.paragraph_format.left_indent = Inches(0.25)
                            parts = re.split(r'(<b>.*?</b>)', bullet)
                            for part in parts:
                                if not part:
                                    continue
                                r = p.add_run(part[3:-4] if part.startswith('<b>') else part)
                                r.bold = part.startswith('<b>')
                                r.font.size = Pt(int(self.base_font_size))
                                r.font.name = self.font_family
                            continue
                        
                        # Name (first non-empty line)
                        if not name_found and not line_data['is_personal_info'] and not line_data['is_bullet']:
                            p = doc.add_paragraph()
                            run = p.add_run(clean)
                            run.font.size = Pt(int(self.base_font_size + 6))
                            run.bold = True
                            run.font.name = self.font_family
                            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            name_found = True
                        
                        # Contact info
                        elif line_data['is_personal_info'] or line_data['is_contact']:
                            p = doc.add_paragraph(clean)
                            p.runs[0].font.size = Pt(int(self.base_font_size - 1))
                            p.runs[0].font.name = self.font_family
                            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        
                        # MAIN Section headers with custom styling
                        elif line_data['is_main_heading'] and not line_data['is_sub_heading']:
                            # Check if consecutive heading
                            is_consecutive = False
                            if i > 0:
                                prev_line = analyzed_lines[i-1]
                                if prev_line['is_main_heading'] or prev_line['is_sub_heading']:
                                    is_consecutive = True
                            
                            if not is_consecutive:
                                p = doc.add_paragraph()
                                run = p.add_run(clean.upper())
                                run.font.size = Pt(int(self.base_font_size + 2))
                                run.bold = True
                                run.font.name = self.font_family
                                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                self.set_paragraph_spacing(p, before=12, after=8, line_spacing=1.0)
                                self.add_paragraph_shading(p, self.highlight_color)
                            else:
                                # Consecutive heading - format as bold but not highlighted
                                p = doc.add_paragraph()
                                run = p.add_run(clean)
                                run.font.size = Pt(int(self.base_font_size + 1))
                                run.bold = True
                                run.font.name = self.font_family
                                p.space_before = Pt(8)
                                p.space_after = Pt(4)
                        
                        # SUB-headings - format as bold but NOT highlighted
                        elif line_data['is_sub_heading']:
                            p = doc.add_paragraph()
                            run = p.add_run(clean)
                            run.font.size = Pt(int(self.base_font_size + 1))
                            run.bold = True
                            run.font.name = self.font_family
                            p.space_before = Pt(6)
                            p.space_after = Pt(3)
                        
                        # Other content
                        else:
                            p = doc.add_paragraph(clean)
                            p.runs[0].font.size = Pt(int(self.base_font_size))
                            p.runs[0].font.name = self.font_family
                            if len(clean) > 100:
                                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                
                doc.save(output_path)
                print(f"✅ Merged DOCX with custom styling saved: {output_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error generating merged {format}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ==================== MAIN ORCHESTRATOR WITH CUSTOMIZATION ====================
    
    def generate_all_documents(
        self,
        ai_response: str,
        session_id: str,
        output_folder: str,
        format: Literal['docx', 'pdf', 'both'] = 'docx',
        merge: Union[bool, Literal['pdf', 'docx', 'both']] = False,
        customization: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Main method to generate all documents with customization options
        
        Args:
            ai_response: AI response containing CV and cover letter
            session_id: Unique session identifier
            output_folder: Output folder path
            format: Output format(s)
            merge: Whether to create merged document(s)
            customization: Customization settings from frontend
            
        Returns:
            Dictionary of generated file paths or None if failed
        """
        print("=" * 60)
        print("🎨 GENERATING DOCUMENTS WITH CUSTOM STYLING")
        print("=" * 60)
        
        # Apply customization if provided
        if customization:
            highlight_color = customization.get('highlight_color', self.highlight_color)
            font_family = customization.get('font_family', self.font_family)
            base_font_size_str = customization.get('base_font_size')
            
            # Ensure highlight_color is a string
            if not isinstance(highlight_color, str):
                highlight_color = 'BFBFBF'
            
            # Ensure font_family is a string
            if not isinstance(font_family, str):
                font_family = 'Calibri'
            
            # Convert base_font_size to float safely
            base_font_size = self.base_font_size  # Default to current
            if base_font_size_str is not None:
                try:
                    base_font_size = float(base_font_size_str)
                except (ValueError, TypeError):
                    base_font_size = self.base_font_size
            
            self.set_customization(highlight_color, font_family, base_font_size)
        
        print(f"✨ Customization Applied:")
        print(f"   • Highlight Color: #{self.highlight_color}")
        print(f"   • Font Family: {self.font_family}")
        print(f"   • Base Font Size: {self.base_font_size}pt")
        print("=" * 60)
        
        if not ai_response or not isinstance(ai_response, str):
            print("❌ Invalid AI response provided")
            return None
        
        if not session_id:
            print("❌ No session ID provided")
            return None
        
        # Create output folder
        os.makedirs(output_folder, exist_ok=True)
        print(f"📁 Output folder ready: {output_folder}")
        
        # Extract documents from AI response
        cv_content, cover_content = self.extract_documents_from_response(ai_response)
        if not cv_content:
            print("❌ Failed to extract CV content")
            return None
        
        results: Dict[str, str] = {}
        success_count = 0
        
        # Individual Files
        if format in ['docx', 'both']:
            cv_path = os.path.join(output_folder, f"{session_id}_cv.docx")
            if self.generate_cv_docx(cv_content, cv_path):
                results['cv_docx'] = cv_path
                success_count += 1
                print(f"✅ Generated CV DOCX: {cv_path}")
            
            if cover_content:
                cover_path = os.path.join(output_folder, f"{session_id}_cover_letter.docx")
                if self.generate_cover_letter_docx(cover_content, cover_path):
                    results['cover_docx'] = cover_path
                    success_count += 1
                    print(f"✅ Generated Cover Letter DOCX: {cover_path}")
        
        if format in ['pdf', 'both']:
            cv_path = os.path.join(output_folder, f"{session_id}_cv.pdf")
            if self.generate_cv_pdf(cv_content, cv_path):
                results['cv_pdf'] = cv_path
                success_count += 1
                print(f"✅ Generated CV PDF: {cv_path}")
            
            if cover_content:
                cover_path = os.path.join(output_folder, f"{session_id}_cover_letter.pdf")
                if self.generate_cover_letter_pdf(cover_content, cover_path):
                    results['cover_pdf'] = cover_path
                    success_count += 1
                    print(f"✅ Generated Cover Letter PDF: {cover_path}")
        
        # Merged Output
        if merge and cover_content:
            merge_options: list[str] = []
            if merge == 'both':
                merge_options = ['pdf', 'docx']
            elif merge in ['pdf', 'docx']:
                merge_options = [merge]
            elif merge is True:
                merge_options = ['pdf']  # Default to PDF if merge=True
            
            for fmt in merge_options:
                ext = fmt
                merged_path = os.path.join(output_folder, f"{session_id}_application_package.{ext}")
                if self.generate_merged_output(cv_content, cover_content, merged_path, format=fmt):
                    results[f'merged_{fmt}'] = merged_path
                    success_count += 1
                    print(f"✅ Generated merged {fmt.upper()}: {merged_path}")
        
        print("=" * 60)
        print(f"✅ SUCCESSFULLY GENERATED {success_count} FILES")
        
        if results:
            print("📋 Generated files:")
            for file_type, file_path in results.items():
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"   • {file_type}: {file_path} ({file_size:,} bytes)")
                else:
                    print(f"   • {file_type}: {file_path} (File not found)")
        
        print("=" * 60)
        return results if results else None


# ==================== DEMO ====================

if __name__ == "__main__":
    # Sample AI response (same as in your app.py)
    sample_ai_response = """
===OPTIMIZED_CV_START===
**IVAN MOUNDE**

📞 +254 741 206 078 | 📧 ivanmounde@gmail.com | 📍 Nairobi, Kenya
**LinkedIn:** www.linkedin.com/in/ivan-mounde-776499201

**Professional Summary**

Goal-oriented and results-driven Data Analyst with 3+ years of experience transforming complex datasets into actionable insights. Proficient in SQL, Python, R, Tableau, Power BI, and Excel, with expertise in KPI dashboard development. Adept at bridging the gap between development, program monitoring, evaluation, and statistical analysis technical outputs and strategic decision-making to drive measurable organizational impact. Passionate about applying data to inform policy, optimize processes, and deliver sustainable results across both private and development sectors.

**Skills**

**Technical Skills**
• Data Analysis: Python, R, SQL, Excel
• Visualization: Tableau, Power BI, matplotlib
• Database: MySQL, PostgreSQL, MongoDB

**Soft Skills**
• Communication: Presentations, Stakeholder Management
• Leadership: Team Management, Project Coordination
• Problem Solving: Analytical Thinking, Decision Making

**Work Experience**

**TOP IMAGE AFRICA** (A leading field marketing and experiential agency in Africa, specializing in brand activations, trade marketing, and consumer engagement across multiple sectors.)

**06/2024 -- Present**

**Data Analyst**

**Key Responsibilities**
• Leads Program Monitoring & Evaluation (M&E) by designing and tracking KPIs across organizational initiatives, ensuring continuous improvement in program outcomes.
• Applies advanced Data Collection, Analysis & Interpretation techniques using SQL, Python, and Power BI to identify patterns and trends that supported evidence-based decision-making.
• Conducts Research & Policy Analysis, translating raw data into insights that guide policy shifts and strategic initiatives.

**Key Achievements**
• Increased decision-making efficiency by **30%** through the implementation of real-time KPI dashboards that improved cross-team collaboration and organizational strategy alignment.

**Education**

**Master of Science, Data Science** | The University of Nairobi | Ongoing
**Bachelor of Science, Statistics** | Taita Taveta University | 2021

**Certifications**

**Professional Certifications**
• Google Data Analytics Professional Certificate
• Microsoft Certified: Azure Data Fundamentals

**Technical Certifications**
• Tableau Desktop Specialist
• SQL Developer Certification

**References**

**Mr. Albert K. Rotich**
Chief Economist
State Department of Housing and Urban Development
Tel: +254 700 000 001
Email: referee1@example.com

**Mr. Jones E. Nyangweso**
Deputy Director, Lands Administration Officer
Ministry of Lands and Physical Planning
Tel: +254 700 000 002
Email: referee2@example.com
===OPTIMIZED_CV_END===

===COVER_LETTER_START===
Ivan Mounde
123 Main Street
Nairobi, Kenya
ivanmounde@gmail.com
+254-741-206-078

[DATE]

Hiring Manager
Data Analytics Department
Company Name
Nairobi, Kenya

Dear Hiring Manager,

I am writing to express my strong interest in the Data Analyst position at your esteemed organization. With over three years of experience as a Data Analyst, I have developed a unique skill set that perfectly aligns with the analytical and strategic thinking required for modern data-driven roles.

Throughout my career, I have consistently leveraged data to drive business performance and optimize organizational strategies. My experience analyzing complex datasets, identifying trends, and creating data-driven solutions has prepared me to make immediate contributions to your team. I am particularly excited about the opportunity to apply my analytical mindset to help your organization achieve its strategic objectives and expand its data capabilities.

My background in statistics and hands-on experience with program monitoring and evaluation has given me deep insights into data-driven decision-making processes. I am confident that my ability to translate complex data into actionable insights, combined with my passion for continuous improvement, makes me an ideal candidate for this role.

I would welcome the opportunity to discuss how my unique combination of analytical expertise and business acumen can benefit your data analytics team. Thank you for considering my application.

Sincerely,

Ivan Mounde
===COVER_LETTER_END===
"""
    
    # Test with different customization settings
    print("🧪 Testing document generation with different customizations...")
    
    # Test 1: Default settings
    print("\n🔹 Test 1: Default Settings")
    generator = ImprovedDocumentGenerator()
    results = generator.generate_all_documents(
        ai_response=sample_ai_response,
        session_id="test_default",
        output_folder="test_output",
        format='docx',
        merge=False
    )
    
    # Test 2: Custom settings (Light Blue, Arial, 11pt)
    print("\n🔹 Test 2: Custom Settings (Light Blue, Arial, 11pt)")
    generator2 = ImprovedDocumentGenerator(
        highlight_color='D4EDFF',
        font_family='Arial',
        base_font_size=11.0
    )
    results2 = generator2.generate_all_documents(
        ai_response=sample_ai_response,
        session_id="test_custom",
        output_folder="test_output",
        format='docx',
        merge=False
    )
    
    # Test 3: With customization dict (like from frontend)
    print("\n🔹 Test 3: With Frontend Customization Dict")
    generator3 = ImprovedDocumentGenerator()
    customization = {
        'highlight_color': 'FFE5D4',  # Light Peach
        'font_family': 'Georgia',
        'base_font_size': '10.5'
    }
    results3 = generator3.generate_all_documents(
        ai_response=sample_ai_response,
        session_id="test_frontend",
        output_folder="test_output",
        format='both',
        merge='both',
        customization=customization
    )
    
    print("\n✅ All tests completed successfully!")
    print("📁 Check the 'test_output' folder for generated documents.")