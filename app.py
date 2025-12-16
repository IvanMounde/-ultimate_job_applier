#!/usr/bin/env python3
# app.py - FULLY FACTORED VERSION WITH EMAIL SUPPORT AND DOCUMENT REGENERATION
# ----------------------------------------------------------------------------
# COMPLETE INTEGRATION WITH DOCUMENT_PROCESSOR.PY
# ENHANCED EMAIL FUNCTIONALITY WITH .ENV CONFIGURATION
# DOCUMENT REGENERATION WITH USER FEEDBACK
# AUTOMATED AI-GENERATED EMAIL CONTENT
# ----------------------------------------------------------------------------

from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
import os
import threading
import time
import re
from datetime import datetime
import uuid
import atexit
import json
from typing import Optional, Dict, Any, List, Tuple, Union, Literal
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate
import mimetypes

# Import Selenium components at the top level to fix "possibly unbound" issues
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# Import the improved document generator
from improved_document_generator import ImprovedDocumentGenerator

# ========== IMPORT YOUR DOCUMENT_PROCESSOR ==========
try:
    from document_processor import DocumentProcessor as YourDocumentProcessor
    DOCUMENT_PROCESSOR_AVAILABLE = True
    print("✅ Successfully imported your document_processor.py")
except ImportError as e:
    print(f"❌ Error importing document_processor.py: {e}")
    DOCUMENT_PROCESSOR_AVAILABLE = False
    YourDocumentProcessor = None
# ====================================================

# ==================== LOAD ENVIRONMENT VARIABLES ====================
load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)

# Configuration
app.config.update({
    'UPLOAD_FOLDER': 'uploads',
    'GENERATED_FOLDER': 'generated_documents',
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB max file size
    'DEBUG': True,
    'SECRET_KEY': 'your-secret-key-here'  # Change this in production!
})

# Ensure directories exist
for folder in [app.config['UPLOAD_FOLDER'], app.config['GENERATED_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

# Global variables
processing_status: Dict[str, Dict[str, Any]] = {}
deepseek_processor: Optional['DeepSeekAutomation'] = None
app_initialized = False

# ========== INITIALIZE YOUR DOCUMENT PROCESSOR ==========
if DOCUMENT_PROCESSOR_AVAILABLE and YourDocumentProcessor:
    try:
        your_document_processor = YourDocumentProcessor()
        print("✅ Your document processor initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize document processor: {e}")
        your_document_processor = None
        DOCUMENT_PROCESSOR_AVAILABLE = False
else:
    your_document_processor = None
    print("⚠️ Document processor not available")
# =======================================================

# ==================== EMAIL CONFIGURATION ====================

class EmailConfig:
    """Email configuration from environment variables"""
    
    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Get email configuration from environment variables"""
        smtp_port_str: Optional[str] = os.getenv('EMAIL_PORT', '587')
        max_size_str: Optional[str] = os.getenv('MAX_EMAIL_SIZE_MB', '10')
        
        try:
            smtp_port = int(smtp_port_str) if smtp_port_str else 587
        except (ValueError, TypeError):
            smtp_port = 587
        
        try:
            max_size = int(max_size_str) if max_size_str else 10
        except (ValueError, TypeError):
            max_size = 10
        
        config: Dict[str, Any] = {
            'SMTP_SERVER': os.getenv('EMAIL_HOST', 'smtp.gmail.com'),
            'SMTP_PORT': smtp_port,
            'SENDER_EMAIL': os.getenv('EMAIL_HOST_USER', ''),
            'SENDER_PASSWORD': os.getenv('EMAIL_HOST_PASSWORD', ''),
            'USE_TLS': (os.getenv('EMAIL_USE_TLS', 'True') or 'True').lower() == 'true',
            'USE_SSL': (os.getenv('EMAIL_USE_SSL', 'False') or 'False').lower() == 'true',
            'DEFAULT_FROM': os.getenv('DEFAULT_FROM_EMAIL', os.getenv('EMAIL_HOST_USER', '')),
            'SUBJECT_PREFIX': os.getenv('EMAIL_SUBJECT_PREFIX', ''),  # Empty by default
            'MAX_SIZE_MB': max_size
        }
        return config
    
    @staticmethod
    def validate() -> bool:
        """Validate email configuration"""
        config = EmailConfig.get_config()
        missing: List[str] = []
        
        sender_email: Optional[str] = config['SENDER_EMAIL']
        sender_password: Optional[str] = config['SENDER_PASSWORD']
        
        if not sender_email:
            missing.append('EMAIL_HOST_USER (your Gmail address)')
        if not sender_password:
            missing.append('EMAIL_HOST_PASSWORD (your Google App Password)')
        
        if missing:
            print(f"⚠️ Email configuration missing: {', '.join(missing)}")
            print("   Please add these to your .env file")
            return False
        
        # Ensure sender_email and sender_password are not None
        if sender_email is None or sender_password is None:
            print("⚠️ Email configuration incomplete")
            return False
        
        print(f"✅ Email configuration loaded for: {sender_email}")
        print(f"   SMTP Server: {config['SMTP_SERVER']}:{config['SMTP_PORT']}")
        print(f"   TLS Enabled: {config['USE_TLS']}")
        return True


# ==================== EMAIL SERVICE CLASS ====================

class EmailService:
    """Handle email sending with attachments using .env configuration"""
    
    def __init__(self):
        self.config = EmailConfig.get_config()
        self.enabled = EmailConfig.validate()
    
    def send_application_email(self, recipient_email: str, subject: str, body: str, 
                              attachments: List[str], cc_emails: Optional[List[str]] = None,
                              bcc_emails: Optional[List[str]] = None, 
                              reply_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Send application email with attachments
        
        Args:
            recipient_email: Primary recipient email
            subject: Email subject
            body: Email body text
            attachments: List of file paths to attach
            cc_emails: List of CC email addresses
            bcc_emails: List of BCC email addresses
            reply_to: Reply-to email address
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Check if email service is enabled
            if not self.enabled:
                return {
                    'success': False,
                    'error': 'Email service not configured. Please check your .env file.'
                }
            
            print(f"📧 Preparing to send email to: {recipient_email}")
            print(f"   Subject: {subject}")
            print(f"   Attachments: {len(attachments)} files")
            
            # Validate recipient
            if not recipient_email or '@' not in recipient_email:
                return {'success': False, 'error': 'Invalid recipient email'}
            
            # Get sender credentials
            sender_email = self.config.get('SENDER_EMAIL')
            sender_password = self.config.get('SENDER_PASSWORD')
            
            if not sender_email or not sender_password:
                return {
                    'success': False,
                    'error': 'Email credentials not found in configuration'
                }
            
            sender_email_str = str(sender_email)
            sender_password_str = str(sender_password)
            
            # Validate attachment size
            total_size = 0
            valid_attachments = []
            for file_path in attachments:
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    
                    # Check individual file size (Gmail limit: 25MB)
                    if file_size > 25 * 1024 * 1024:
                        print(f"   ⚠️ Skipping {os.path.basename(file_path)}: Exceeds 25MB limit")
                        continue
                    
                    valid_attachments.append(file_path)
                else:
                    print(f"   ⚠️ Attachment not found: {file_path}")
            
            # Check total size
            if total_size > self.config['MAX_SIZE_MB'] * 1024 * 1024:
                return {
                    'success': False, 
                    'error': f'Total attachment size exceeds {self.config["MAX_SIZE_MB"]}MB limit'
                }
            
            if not valid_attachments:
                return {'success': False, 'error': 'No valid attachments found'}
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email_str
            msg['To'] = recipient_email
            
            # Add subject (WITHOUT prefix for cleaner emails)
            msg['Subject'] = subject.strip()
            
            msg['Date'] = formatdate(localtime=True)
            
            # Add Reply-To if provided
            if reply_to:
                msg['Reply-To'] = reply_to
            else:
                msg['Reply-To'] = sender_email_str
            
            # Add CC if provided
            cc_list = []
            if cc_emails:
                cc_list = [email.strip() for email in cc_emails if self._validate_email(email.strip())]
                if cc_list:
                    msg['Cc'] = ', '.join(cc_list)
            
            # Add BCC if provided
            bcc_list = []
            if bcc_emails:
                bcc_list = [email.strip() for email in bcc_emails if self._validate_email(email.strip())]
            
            # Add body
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Add attachments
            for file_path in valid_attachments:
                filename = os.path.basename(file_path)
                
                try:
                    with open(file_path, 'rb') as file:
                        # Try to guess MIME type
                        mime_type, encoding = mimetypes.guess_type(file_path)
                        
                        if mime_type is None or encoding is not None:
                            mime_type = 'application/octet-stream'
                        
                        main_type, sub_type = mime_type.split('/', 1)
                        
                        if main_type == 'text':
                            part = MIMEText(file.read().decode('utf-8', errors='ignore'), _subtype=sub_type)
                        else:
                            part = MIMEBase(main_type, sub_type)
                            part.set_payload(file.read())
                            encoders.encode_base64(part)
                        
                        part.add_header('Content-Disposition', 'attachment', filename=filename)
                        msg.attach(part)
                        
                        print(f"   ✅ Attached: {filename} ({os.path.getsize(file_path):,} bytes)")
                        
                except Exception as e:
                    print(f"   ❌ Failed to attach {filename}: {e}")
            
            # Send email
            print(f"   🔌 Connecting to SMTP server: {self.config['SMTP_SERVER']}:{self.config['SMTP_PORT']}")
            
            with smtplib.SMTP(self.config['SMTP_SERVER'], self.config['SMTP_PORT'], timeout=30) as server:
                server.set_debuglevel(1)  # Enable debug output
                
                if self.config['USE_TLS']:
                    print("   🔒 Starting TLS...")
                    server.starttls()
                
                print(f"   👤 Logging in as: {sender_email_str}")
                server.login(sender_email_str, sender_password_str)
                
                # Build recipient list
                all_recipients = [recipient_email]
                if cc_emails:
                    all_recipients.extend(cc_list)
                if bcc_emails:
                    all_recipients.extend(bcc_list)
                
                # Remove duplicates
                all_recipients = list(dict.fromkeys(all_recipients))
                
                print(f"   📤 Sending to {len(all_recipients)} recipients...")
                server.send_message(msg)
                print("   ✅ Email sent successfully!")
            
            return {
                'success': True,
                'message': f'Email sent successfully to {recipient_email}',
                'recipient_count': len(all_recipients),
                'attachment_count': len(valid_attachments),
                'total_size_bytes': total_size
            }
            
        except smtplib.SMTPAuthenticationError:
            error_msg = "Authentication failed. Please check your email and app password in .env file"
            print(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            print(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg}
        except Exception as e:
            print(f"❌ Email sending failed: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def _validate_email(self, email: str) -> bool:
        """Basic email validation"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def send_test_email(self, test_recipient: Optional[str] = None) -> Dict[str, Any]:
        """Send a test email to verify configuration"""
        if not test_recipient:
            test_recipient = self.config.get('SENDER_EMAIL', '')
        
        if not test_recipient:
            return {
                'success': False,
                'error': 'No recipient specified and no default sender email configured'
            }
        
        test_body = f"""This is a test email from the AI Job Application Assistant.

If you're receiving this email, your email configuration is working correctly!

System Status: ✅ Ready
Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
SMTP Server: {self.config['SMTP_SERVER']}:{self.config['SMTP_PORT']}

Best regards,
AI Job Application Assistant"""
        
        return self.send_application_email(
            recipient_email=str(test_recipient),
            subject="Test Email - AI Job Application Assistant",
            body=test_body,
            attachments=[]
        )


# Initialize email service globally
email_service = EmailService()


# ==================== DEEPSEEK AUTOMATION CLASS ====================

class DeepSeekAutomation:
    """Handle DeepSeek AI automation with enhanced error handling"""
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.initialized = False
    
    def setup_chrome(self) -> bool:
        """Setup Chrome with remote debugging"""
        try:
            print("🔴 Closing Chrome...")
            self.kill_chrome_processes()
            
            print("🟢 Starting Chrome with debugging...")
            
            # Start Chrome process
            import subprocess
            
            chrome_paths = [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
                os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe")
            ]
            
            chrome_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break
            
            if not chrome_path:
                print("❌ Chrome not found in standard locations")
                return False
            
            user_data_dir = "C:\\Temp\\ChromeDebug"
            os.makedirs(user_data_dir, exist_ok=True)
            
            # Start Chrome with remote debugging
            subprocess.Popen([
                chrome_path,
                "--remote-debugging-port=9222",
                f"--user-data-dir={user_data_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "https://chat.deepseek.com"
            ])
            
            print("⏳ Waiting for Chrome to start...")
            time.sleep(8)
            
            # Connect to existing Chrome instance
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            print("✅ Chrome started and connected!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup Chrome: {e}")
            return False
    
    def wait_for_deepseek_load(self) -> bool:
        """Wait for DeepSeek to load"""
        try:
            if not self.driver:
                return False
                
            print("⏳ Waiting for DeepSeek to load...")
            
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Try to find the chat input
            input_selectors = [
                "textarea[placeholder*='Message']",
                "textarea[placeholder*='message']",
                "textarea[placeholder*='Send']",
                "textarea",
                "input[type='text']"
            ]
            
            for selector in input_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if element.is_displayed():
                        print(f"✅ Found input element with selector: {selector}")
                        self.initialized = True
                        return True
                except:
                    continue
            
            print("❌ Could not find chat input element")
            return False
            
        except Exception as e:
            print(f"❌ Error waiting for DeepSeek: {e}")
            return False
    
    def kill_chrome_processes(self) -> None:
        """Kill all Chrome processes"""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                    try:
                        psutil.Process(proc.info['pid']).terminate()
                        print(f"SUCCESS: The process 'chrome.exe' with PID {proc.info['pid']} has been terminated.")
                    except:
                        pass
            time.sleep(3)
        except ImportError:
            print("⚠️ psutil not available, using taskkill for Chrome cleanup")
            os.system("taskkill /f /im chrome.exe >nul 2>&1")
        except Exception as e:
            print(f"Warning killing Chrome processes: {e}")
            os.system("taskkill /f /im chrome.exe >nul 2>&1")
    
    def keep_alive(self) -> bool:
        """Check if browser is still alive"""
        try:
            if self.driver:
                _ = self.driver.current_url
                return True
        except:
            pass
        return False
    
    def clear_chat_history(self) -> bool:
        """Clear chat history to ensure fresh response"""
        try:
            if not self.driver:
                return False
                
            print("🧹 Clearing chat history for fresh generation...")
            
            # Try multiple methods to clear chat
            clear_methods = [
                self._clear_via_new_chat_button,
                self._clear_via_reset_button,
                self._clear_via_url_refresh
            ]
            
            for method in clear_methods:
                if method():
                    print("✅ Chat cleared successfully")
                    return True
            
            print("⚠️ Could not clear chat history, but will proceed")
            return False
            
        except Exception as e:
            print(f"❌ Error clearing chat: {e}")
            return False
    
    def _clear_via_new_chat_button(self) -> bool:
        """Try to clear via new chat button"""
        try:
            if not self.driver:
                return False
            
            new_chat_selectors = [
                "button[class*='new-chat']",
                "button[class*='new']",
                "a[href*='new']",
                "[data-testid='new-chat-button']",
                ".new-chat",
            ]
            
            for selector in new_chat_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            time.sleep(3)
                            return True
                except:
                    continue
        except Exception as e:
            print(f"❌ New chat method failed: {e}")
        
        return False
    
    def _clear_via_reset_button(self) -> bool:
        """Try to clear via reset or clear button"""
        try:
            if not self.driver:
                return False
            
            reset_selectors = [
                "button[class*='clear']",
                "button[class*='reset']",
            ]
            
            for selector in reset_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            time.sleep(2)
                            return True
                except:
                    continue
        except Exception as e:
            print(f"❌ Reset method failed: {e}")
        
        return False
    
    def _clear_via_url_refresh(self) -> bool:
        """Refresh the page to clear context"""
        try:
            if not self.driver:
                return False
                
            self.driver.get("https://chat.deepseek.com")
            time.sleep(5)
            return self.wait_for_deepseek_load()
        except Exception as e:
            print(f"❌ URL refresh failed: {e}")
            return False
    
    def get_comprehensive_response(self, prompt: str) -> Optional[str]:
        """Send prompt and get comprehensive response with complete content capture"""
        if not self.initialized or not self.driver:
            print("❌ DeepSeek not initialized")
            return None
        
        try:
            # Clear chat history first to ensure fresh response
            self.clear_chat_history()
            
            print("🔍 Looking for main chat input...")
            
            import pyperclip
            
            # Try various selectors for the chat input
            input_selectors = [
                "textarea[placeholder*='Message']",
                "textarea[placeholder*='message']", 
                "textarea[placeholder*='Send']",
                "textarea",
                "input[type='text']"
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if element.is_displayed() and element.is_enabled():
                        input_element = element
                        print(f"✅ Found input element with selector: {selector}")
                        break
                except:
                    continue
            
            if not input_element:
                print("❌ Could not find chat input element")
                return None
            
            # Clear any existing text
            input_element.clear()
            time.sleep(1)
            
            # Step 1: Verify prompt completeness
            print("🔍 Verifying prompt completeness...")
            print(f"📊 Prompt length: {len(prompt)} characters")
            print(f"📊 Prompt preview (first 500 chars): {prompt[:500]}...")
            print(f"📊 Prompt preview (last 500 chars): ...{prompt[-500:]}")
            
            # Check if prompt has essential markers
            essential_markers = [
                "===OPTIMIZED_CV_START===",
                "===OPTIMIZED_CV_END===",
                "===COVER_LETTER_START===",
                "===COVER_LETTER_END===",
                "===EMAIL_CONTENT_START===",
                "===EMAIL_CONTENT_END==="
            ]
            
            missing_markers = []
            for marker in essential_markers:
                if marker not in prompt:
                    missing_markers.append(marker)
            
            if missing_markers:
                print(f"⚠️ WARNING: Prompt missing essential markers: {missing_markers}")
                print("⚠️ This may affect document generation quality.")
            
            # Step 2: COPY COMPLETE PROMPT TO CLIPBOARD
            print("📋 Copying COMPLETE prompt to clipboard...")
            try:
                pyperclip.copy(prompt)
                time.sleep(2)  # Ensure clipboard has time to process
                print("✅ Prompt copied to clipboard successfully")
            except Exception as e:
                print(f"❌ Failed to copy to clipboard: {e}")
                print("🔄 Falling back to direct input method...")
                return self._send_prompt_directly(input_element, prompt)
            
            # Step 3: PASTE COMPLETE PROMPT ALL AT ONCE
            print("📤 Pasting COMPLETE prompt into DeepSeek...")
            
            # Focus on input element
            input_element.click()
            time.sleep(1)
            
            # Use Ctrl+A to select any existing text (should be empty but just in case)
            actions = ActionChains(self.driver)
            actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
            time.sleep(0.5)
            
            # Paste using Ctrl+V
            actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            time.sleep(3)  # Give time for complete paste to finish
            
            # Step 4: VERIFY PASTE COMPLETENESS
            print("🔍 Verifying paste completeness...")
            pasted_text = input_element.get_attribute('value') or input_element.text or input_element.get_attribute('innerText')
            
            if not pasted_text:
                # Try alternative method to get text
                try:
                    pasted_text = input_element.get_property('value')
                except:
                    try:
                        pasted_text = self.driver.execute_script("return arguments[0].value", input_element)
                    except:
                        pasted_text = ""
            
            # FIX: Safe length check with proper type handling
            pasted_text_str = str(pasted_text) if pasted_text else ""
            actual_length = len(pasted_text_str)
            expected_length = len(prompt)
            
            print(f"📊 Paste verification:")
            print(f"   • Expected: {expected_length} characters")
            print(f"   • Actual: {actual_length} characters")
            print(f"   • Completion: {(actual_length/expected_length)*100:.1f}%" if expected_length > 0 else "   • Completion: 0%")
            
            # Check if paste was successful
            if actual_length < expected_length * 0.9:  # Less than 90% of expected
                print(f"⚠️ Clipboard paste incomplete! Only {actual_length}/{expected_length} characters.")
                print("🔄 Retrying with alternative paste method...")
                
                # Clear and retry with JavaScript paste
                input_element.clear()
                time.sleep(1)
                
                # Use JavaScript to set value directly
                try:
                    self.driver.execute_script("arguments[0].value = arguments[1];", input_element, prompt)
                    time.sleep(2)
                    
                    # Verify JavaScript paste
                    js_pasted_text = self.driver.execute_script("return arguments[0].value", input_element)
                    js_pasted_text_str = str(js_pasted_text) if js_pasted_text else ""
                    js_length = len(js_pasted_text_str)
                    print(f"📊 JavaScript paste: {js_length}/{expected_length} characters")
                    
                    if js_length >= expected_length * 0.95:
                        pasted_text = js_pasted_text
                        actual_length = js_length
                        print("✅ JavaScript paste successful!")
                    else:
                        print("⚠️ JavaScript paste also incomplete, falling back to chunked input...")
                        return self._send_prompt_directly(input_element, prompt)
                except Exception as js_error:
                    print(f"❌ JavaScript paste failed: {js_error}")
                    return self._send_prompt_directly(input_element, prompt)
            
            # Step 5: Additional verification - check for key markers in pasted text
            print("🔍 Checking for essential markers in pasted text...")
            markers_found = 0
            for marker in essential_markers:
                if marker in pasted_text_str:
                    markers_found += 1
                    print(f"   ✅ Found: {marker}")
                else:
                    print(f"   ❌ Missing: {marker}")
            
            if markers_found >= 3:  # At least CV, Cover Letter and Email markers should be present
                print(f"✅ Essential markers found: {markers_found}/6")
            else:
                print(f"⚠️ Warning: Only {markers_found}/6 essential markers found in pasted text")
            
            # Step 6: SEND THE COMPLETE PROMPT
            print("✅ COMPLETE PROMPT successfully pasted, pressing Enter to send...")
            input_element.send_keys(Keys.ENTER)
            
            print("🚀 Prompt sent to DeepSeek AI!")
            print("⏳ Waiting for comprehensive response (this may take 5-8 minutes)...")
            
            # Wait for completion
            return self.wait_for_completion_enhanced()
            
        except Exception as e:
            print(f"❌ Error sending prompt: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _send_prompt_directly(self, input_element: Any, prompt: str) -> Optional[str]:
        """Fallback method: send prompt directly in chunks if clipboard fails"""
        try:
            print("🔄 Using direct input method (chunked)...")
            input_element.clear()
            time.sleep(1)
            
            # Use optimized chunk size for better performance
            chunk_size = 1500  # Smaller chunks for reliability
            total_chunks = (len(prompt) + chunk_size - 1) // chunk_size
            
            print(f"📊 Sending {total_chunks} chunks of {chunk_size} characters each...")
            
            for i in range(0, len(prompt), chunk_size):
                chunk = prompt[i:i + chunk_size]
                chunk_number = (i // chunk_size) + 1
                
                input_element.send_keys(chunk)
                print(f"   📦 Sent chunk {chunk_number}/{total_chunks} ({len(chunk)} chars)")
                
                # Small delay between chunks, but not after the last one
                if i + chunk_size < len(prompt):
                    time.sleep(0.3)  # Very short delay to prevent overwhelming the browser
            
            # Final verification
            final_text = input_element.get_attribute('value') or input_element.text
            final_text_str = str(final_text) if final_text else ""
            final_length = len(final_text_str)
            print(f"📊 Direct input complete: {final_length}/{len(prompt)} characters")
            
            if final_length >= len(prompt) * 0.95:
                print("✅ Direct input successful, pressing Enter...")
                input_element.send_keys(Keys.ENTER)
                return self.wait_for_completion_enhanced()
            else:
                print("❌ Direct input failed to send complete prompt")
                return None
                
        except Exception as e:
            print(f"❌ Error in direct input method: {e}")
            return None

    def wait_for_completion_enhanced(self, timeout: int = 600) -> Optional[str]:
        """Wait for AI response to complete with better detection"""
        if not self.initialized or not self.driver:
            return None
        
        start_time = time.time()
        last_response_length = 0
        stable_count = 0
        max_stable_checks = 8
        check_interval = 8
        min_response_length = 1000
        
        print("⏳ Waiting for comprehensive AI response (this may take 5-8 minutes)...")
        print("   Looking for typing indicators to stop...")
        
        # First, wait for AI to START responding
        typing_started = False
        wait_for_start = 30
        
        for i in range(wait_for_start):
            if self._is_deepseek_typing():
                typing_started = True
                print("✅ AI started generating response...")
                break
            time.sleep(1)
        
        if not typing_started:
            print("⚠️ No typing indicator detected, waiting 10 seconds...")
            time.sleep(10)
        
        # Now wait for response to complete
        while time.time() - start_time < timeout:
            try:
                # Check if still typing
                is_typing = self._is_deepseek_typing()
                
                if is_typing:
                    elapsed = int(time.time() - start_time)
                    print(f"🤖 DeepSeek is still generating... ({elapsed}s elapsed)")
                    stable_count = 0
                    time.sleep(check_interval)
                    continue
                
                # Not typing anymore, get current response
                current_response = self._get_latest_ai_message()
                current_response_str = str(current_response) if current_response else ""
                current_length = len(current_response_str)
                
                print(f"📊 Response check: {current_length} chars, stable: {stable_count}/{max_stable_checks}")
                
                # Check for completion markers
                if current_response and current_length > min_response_length and self._has_completion_markers(current_response_str):
                    print("✅ Found completion markers in response!")
                    time.sleep(3)
                    return self._get_latest_ai_message()
                
                # Check if response is stable
                if current_length > 0 and current_length == last_response_length:
                    stable_count += 1
                    print(f"✅ Response stable ({stable_count}/{max_stable_checks})")
                else:
                    stable_count = 0
                    last_response_length = current_length
                    if current_length > 0:
                        print(f"📈 Response growing: {current_length} chars")
                
                # If stable for enough checks and has substantial content
                if stable_count >= max_stable_checks and current_length > min_response_length:
                    print("✅ Response complete and stable with substantial content!")
                    return current_response
                
                time.sleep(check_interval)
                
            except Exception as e:
                print(f"⚠️ Error checking response: {e}")
                time.sleep(check_interval)
        
        print("⏰ Timeout reached, getting final response...")
        final_response = self._get_latest_ai_message()
        final_response_str = str(final_response) if final_response else ""
        print(f"📄 Final response length: {len(final_response_str)} characters")
        return final_response

    def _is_deepseek_typing(self) -> bool:
        """Enhanced typing detection"""
        if not self.initialized or not self.driver:
            return False
        
        typing_indicators = [
            "[class*='typing']",
            "[class*='thinking']",
            "[class*='loading']",
            "[class*='animate']",
            "[class*='generating']",
            "[class*='spinner']",
            "[class*='pulse']",
            "button[disabled]",
            "svg[class*='animate']",
        ]
        
        try:
            for indicator in typing_indicators:
                elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                for elem in elements:
                    try:
                        if elem.is_displayed():
                            parent_classes = elem.get_attribute("class") or ""
                            if "message" in parent_classes.lower() or "chat" in parent_classes.lower():
                                return True
                    except:
                        continue
        except Exception as e:
            print(f"⚠️ Error checking typing status: {e}")
        
        return False

    def _get_latest_ai_message(self) -> Optional[str]:
        """Get only the LATEST AI message (not the user's prompt)"""
        if not self.initialized or not self.driver:
            return None
        
        try:
            message_selectors = [
                "[class*='message']",
                "[class*='response']",
                "[class*='assistant']",
                "[class*='ai']",
                ".markdown-body",
                "[role='article']"
            ]
            
            all_messages: List[Dict[str, Any]] = []
            
            for selector in message_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            text = elem.text.strip()
                            if text and len(text) > 100:
                                all_messages.append({
                                    'text': text,
                                    'element': elem
                                })
                except:
                    continue
            
            if not all_messages:
                print("⚠️ No messages found, trying full body text...")
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                return body_text
            
            # Get the last message with completion markers
            for msg in reversed(all_messages):
                text = msg['text']
                if any(marker in text for marker in [
                    '===OPTIMIZED_CV', '===COVER_LETTER', '===EMAIL_CONTENT',
                    'PROFESSIONAL SUMMARY', 'Dear Hiring Manager', 'SUBJECT:'
                ]):
                    print(f"✅ Found AI response message: {len(text)} chars")
                    return text
            
            # If no markers, return longest message
            longest_message = max(all_messages, key=lambda x: len(x['text']))
            print(f"📝 Returning longest message: {len(longest_message['text'])} chars")
            return longest_message['text']
            
        except Exception as e:
            print(f"❌ Error getting latest message: {e}")
            try:
                return self.driver.find_element(By.TAG_NAME, "body").text
            except:
                return None

    def _has_completion_markers(self, text: str) -> bool:
        """Check if response has markers indicating completion"""
        if not text:
            return False
        
        completion_indicators = [
            "===COVER_LETTER_END===",
            "===OPTIMIZED_CV_END===",
            "===EMAIL_CONTENT_END===",
            "Sincerely,",
            "Best regards,",
            "Yours truly,",
        ]
        
        has_cv = "===OPTIMIZED_CV" in text or "PROFESSIONAL SUMMARY" in text
        has_cover = "===COVER_LETTER" in text or "Dear Hiring Manager" in text
        has_email = "===EMAIL_CONTENT" in text or "SUBJECT:" in text
        
        if has_cv and has_cover and has_email:
            for marker in completion_indicators:
                if marker in text:
                    return True
        
        return False

    def close(self) -> None:
        """Close the browser"""
        try:
            if self.driver:
                self.driver.quit()
                self.initialized = False
        except:
            pass


# ==================== PROMPT ENGINEERING CLASS ====================

class PromptEngineer:
    """Engineer prompts for optimal AI response formatting"""
    
    @staticmethod
    def get_enhanced_prompt(cv_content: str, job_info: str, customization: Dict[str, Any]) -> str:
        """
        Create optimized prompt that ensures complete CV and job info are sent
        with proper formatting for the document generator
        """
        # Extract customization options
        highlight_color = customization.get('highlight_color', 'BFBFBF')
        font_family = customization.get('font_family', 'Calibri')
        font_size = customization.get('font_size', 10.0)
        
        # Clean and prepare content
        complete_cv = PromptEngineer._ensure_complete_cv(cv_content)
        complete_job_info = PromptEngineer._ensure_complete_job_info(job_info)
        
        prompt = f"""
Generate THREE professional documents with EXACT formatting for automatic processing:

IMPORTANT FORMATTING RULES:
1. Use EXACT delimiters as shown below
2. Structure CV with clear sections using ALL CAPS for main headings
3. Use bullet points starting with • for achievements and responsibilities
4. Include quantifiable metrics like 15%, 30+, etc.
5. Use consistent formatting throughout

DOCUMENT 1: OPTIMIZED RESUME/CV
MUST use these EXACT section headers in ALL CAPS:
- CONTACT INFORMATION
- PROFESSIONAL SUMMARY
- WORK EXPERIENCE (with dates and bullet points)
- EDUCATION (with dates and degrees)
- SKILLS (group into Technical Skills and Soft Skills)
- CERTIFICATIONS (if any)
- REFERENCES (if available)

DOCUMENT 2: PROFESSIONAL COVER LETTER
MUST include:
- Sender's contact info at top
- Date with [DATE] placeholder
- Recipient address
- Formal salutation "Dear Hiring Manager,"
- 2-3 body paragraphs explaining fit
- Formal closing "Sincerely,"
- Signature line with name

DOCUMENT 3: PROFESSIONAL EMAIL CONTENT
Generate a COMPLETE professional email for submitting this job application.
The email should:
1. Be tailored specifically to this job application
2. Reference key requirements from the job description
3. Highlight relevant skills from the CV
4. Be professional yet personable
5. Include appropriate subject line

CUSTOMIZATION PREFERENCES:
- Font: {font_family}
- Base size: {font_size}pt
- Section highlights: #{highlight_color}

USER'S ORIGINAL CV CONTENT:
{complete_cv}

JOB REQUIREMENTS:
{complete_job_info}

KEY TRANSFERABLE SKILLS TO HIGHLIGHT:
1. Analytical & Problem-solving
2. Communication & Stakeholder Management
3. Project Management & Leadership
4. Technical Expertise (Python, SQL, etc.)
5. Results Orientation

NOW CREATE ALL THREE DOCUMENTS WITH EXACT FORMATTING:

===OPTIMIZED_CV_START===
[FULL NAME IN BOLD]

[Contact Information: Phone | Email | LinkedIn | Location]

PROFESSIONAL SUMMARY
[3-4 sentences highlighting key achievements and skills]

WORK EXPERIENCE

[COMPANY NAME] (Company description if available)
[Date Range: MM/YYYY -- Present or MM/YYYY -- MM/YYYY]
[Job Title]

Key Responsibilities:
• [Responsibility 1 with metrics if possible]
• [Responsibility 2 with metrics if possible]

Key Achievements:
• [Achievement 1 with quantifiable results]
• [Achievement 2 with quantifiable results]

EDUCATION

[Degree Name] | [Institution Name] | [Graduation Year]
[Relevant coursework or honors if applicable]

SKILLS

Technical Skills:
• [Skill category]: [Specific skills]
• [Another skill category]: [Specific skills]

Soft Skills:
• [Skill 1]
• [Skill 2]
• [Skill 3]

CERTIFICATIONS
• [Certification 1] | [Issuing Organization] | [Year]
• [Certification 2] | [Issuing Organization] | [Year]

REFERENCES
Available upon request.

===OPTIMIZED_CV_END===

===COVER_LETTER_START===
[Your Full Name]
[Your Address]
[Your City, State, Zip Code]
[Your Email]
[Your Phone Number]

[DATE]

[Hiring Manager Name]
[Hiring Manager Title]
[Company Name]
[Company Address]
[Company City, State, Zip Code]

Dear Hiring Manager,

[First paragraph: Introduce yourself and express interest. Mention the specific position.]

[Second paragraph: Highlight your most relevant skills and experiences. Connect them to the job requirements.]

[Third paragraph: Show enthusiasm for the company/role. Mention any specific achievements or projects that demonstrate your fit.]

[Closing paragraph: Reiterate your interest and request an interview.]

Sincerely,

[Your Full Name]
===COVER_LETTER_END===

===EMAIL_CONTENT_START===
SUBJECT: [Tailored subject line that references the specific job position and shows enthusiasm]

BODY:
Dear [Hiring Manager Name or "Hiring Team"],

[Opening paragraph: Introduce yourself and express genuine interest in the specific position. Mention where you saw the job posting if relevant.]

[Second paragraph: Briefly highlight your most relevant qualifications that match the job requirements. Reference 2-3 key skills or experiences from the CV that align with the job description.]

[Third paragraph: Show enthusiasm for the company/role and mention something specific that attracted you to this opportunity.]

[Closing paragraph: Indicate that your CV and cover letter are attached, express gratitude for consideration, and mention your availability for an interview.]

Best regards,

[Your Full Name]
[Your Phone Number]
[Your Email Address]
===EMAIL_CONTENT_END===

Remember:
1. Use bullet points with • not dashes or asterisks
2. Include metrics like "increased efficiency by 30%" or "managed team of 5+"
3. Keep professional tone throughout
4. Tailor ALL content to the specific job requirements
5. Make the email content PERSONALIZED and RELEVANT
6. Use the EXACT delimiters as shown above
"""
        
        # Add feedback section if present
        cv_feedback = customization.get('cv_feedback', '')
        cover_feedback = customization.get('cover_feedback', '')
        email_feedback = customization.get('email_feedback', '')
        
        if cv_feedback or cover_feedback or email_feedback:
            feedback_section = f"""

IMPORTANT USER FEEDBACK FOR IMPROVEMENT:

CV/RESUME SPECIFIC CHANGES REQUESTED:
{cv_feedback if cv_feedback else "None specified"}

COVER LETTER SPECIFIC CHANGES REQUESTED:
{cover_feedback if cover_feedback else "None specified"}

EMAIL CONTENT SPECIFIC CHANGES REQUESTED:
{email_feedback if email_feedback else "None specified"}

PLEASE INCORPORATE THESE CHANGES INTO THE REGENERATED DOCUMENTS.
Address each feedback point specifically in the regenerated documents.
"""
            prompt += feedback_section
        
        return prompt
    
    @staticmethod
    def _ensure_complete_cv(cv_content: str) -> str:
        """Ensure the CV content is complete and not truncated"""
        if not cv_content:
            return "No CV content provided"
        
        completeness_indicators = ['EDUCATION', 'SKILLS', 'REFERENCES', 'EXPERIENCE', 'WORK']
        has_indicators = any(indicator in cv_content.upper() for indicator in completeness_indicators)
        
        if has_indicators and len(cv_content) > 1000:
            print("✅ CV appears complete")
            return cv_content
        else:
            print("⚠️ CV may be incomplete, using as-is")
            return cv_content
    
    @staticmethod
    def _ensure_complete_job_info(job_info: str) -> str:
        """Ensure the job info is complete and not truncated"""
        if not job_info:
            return "No job information provided"
        
        if len(job_info) > 200 and any(keyword in job_info for keyword in ['Responsibilities', 'Requirements', 'Qualifications']):
            print("✅ Job info appears complete")
            return job_info
        else:
            print("⚠️ Job info may be incomplete, using as-is")
            return job_info
    
    @staticmethod
    def _extract_cv_sections(cv_content: str) -> Dict[str, str]:
        """Extract key sections from CV for prompt enhancement"""
        sections: Dict[str, str] = {
            'contact': '',
            'summary': '',
            'experience': '',
            'education': '',
            'skills': '',
            'achievements': ''
        }
        
        lines = cv_content.split('\n')
        current_section: Optional[str] = None
        
        for line in lines:
            line_upper = line.upper()
            
            if 'CONTACT' in line_upper or 'PHONE' in line_upper or 'EMAIL' in line_upper:
                current_section = 'contact'
            elif 'SUMMARY' in line_upper or 'OBJECTIVE' in line_upper or 'PROFILE' in line_upper:
                current_section = 'summary'
            elif 'EXPERIENCE' in line_upper or 'WORK' in line_upper or 'EMPLOYMENT' in line_upper:
                current_section = 'experience'
            elif 'EDUCATION' in line_upper or 'QUALIFICATION' in line_upper:
                current_section = 'education'
            elif 'SKILL' in line_upper:
                current_section = 'skills'
            elif 'ACHIEVEMENT' in line_upper or 'ACCOMPLISHMENT' in line_upper:
                current_section = 'achievements'
            
            if current_section and line.strip():
                sections[current_section] += line + '\n'
        
        return sections


# ==================== EMAIL CONTENT EXTRACTOR ====================

def extract_email_content_from_response(ai_response: Optional[str]) -> Dict[str, str]:
    """Extract email content from AI response - FIX for missing extract_email_content method"""
    subject = "Application for Position"
    body = "Dear Hiring Manager,\n\nPlease find attached my CV and cover letter for your consideration."
    
    if not ai_response:
        return {'subject': subject, 'body': body}
    
    try:
        # Look for email content section
        if "===EMAIL_CONTENT_START===" in ai_response and "===EMAIL_CONTENT_END===" in ai_response:
            start_idx = ai_response.find("===EMAIL_CONTENT_START===") + len("===EMAIL_CONTENT_START===")
            end_idx = ai_response.find("===EMAIL_CONTENT_END===")
            email_content = ai_response[start_idx:end_idx].strip()
            
            # Extract subject
            for line in email_content.split('\n'):
                if line.strip().startswith('SUBJECT:'):
                    subject = line.replace('SUBJECT:', '').strip()
                    break
            
            # Extract body (skip empty lines and subject)
            body_lines = []
            in_body = False
            for line in email_content.split('\n'):
                line_stripped = line.strip()
                if line_stripped.startswith('SUBJECT:'):
                    continue  # Skip subject line
                elif line_stripped.startswith('BODY:') or 'Dear' in line_stripped or line_stripped:
                    in_body = True
                if in_body and line_stripped:
                    body_lines.append(line_stripped)
            
            if body_lines:
                # Remove 'BODY:' prefix if present
                body_text = '\n'.join(body_lines)
                if body_text.startswith('BODY:'):
                    body_text = body_text[5:].strip()
                body = body_text
    except Exception as e:
        print(f"⚠️ Error extracting email content: {e}")
    
    return {'subject': subject, 'body': body}


# ==================== JOB APPLICATION PROCESSOR CLASS ====================

class JobApplicationProcessor:
    """Main processor for job applications using your document_processor.py"""
    
    def __init__(self, document_processor: Optional[YourDocumentProcessor] = None):
        """Initialize with document processor"""
        if document_processor:
            self.document_processor = document_processor
            print("✅ Using provided document_processor.py for text extraction")
        elif DOCUMENT_PROCESSOR_AVAILABLE and your_document_processor:
            self.document_processor = your_document_processor
            print("✅ Using global document_processor.py for text extraction")
        else:
            raise ImportError("document_processor.py not available. Please ensure it's in the same directory.")
        
        self.prompt_engineer = PromptEngineer()
    
    def process_job_application(self, session_id: str, cv_content: str, 
                               job_info: str, customization: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Main method to process job application"""
        global deepseek_processor
        
        try:
            # Update processing status
            processing_status[session_id] = {
                'status': 'processing',
                'message': 'Initializing AI Assistant...',
                'percentage': 10
            }
            time.sleep(2)
            
            print(f"🎯 Processing CV: {len(cv_content)} chars, Job info: {len(job_info)} chars")
            print(f"🎨 Customization: {customization}")
            
            processing_status[session_id] = {
                'status': 'processing',
                'message': 'Connecting to DeepSeek AI...',
                'percentage': 20
            }
            
            # Initialize or reconnect to DeepSeek
            if not deepseek_processor or not deepseek_processor.keep_alive():
                if not self._initialize_deepseek():
                    processing_status[session_id] = {
                        'status': 'error',
                        'message': 'Failed to connect to DeepSeek AI',
                        'percentage': 0
                    }
                    return None
            
            processing_status[session_id] = {
                'status': 'processing',
                'message': 'Preparing comprehensive prompt...',
                'percentage': 30
            }
            
            # Create optimized prompt with proper formatting
            comprehensive_prompt = self.prompt_engineer.get_enhanced_prompt(
                cv_content, job_info, customization
            )
            
            # Save prompt for debugging (in UPLOAD folder)
            debug_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_prompt.txt")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(comprehensive_prompt)
            print(f"💾 Saved prompt: {len(comprehensive_prompt)} chars to {debug_file}")
            
            processing_status[session_id] = {
                'status': 'processing',
                'message': 'Sending COMPLETE PROMPT to AI (this may take 5-8 minutes)...',
                'percentage': 40
            }
            
            # Get AI response
            if deepseek_processor:
                ai_response = deepseek_processor.get_comprehensive_response(comprehensive_prompt)
            else:
                processing_status[session_id] = {
                    'status': 'error',
                    'message': 'DeepSeek processor not available',
                    'percentage': 0
                }
                return None
            
            if not ai_response:
                processing_status[session_id] = {
                    'status': 'error',
                    'message': 'Failed to get AI response',
                    'percentage': 0
                }
                return None
            
            processing_status[session_id] = {
                'status': 'processing',
                'message': 'Parsing AI response...',
                'percentage': 60
            }
            
            # Save AI response (in UPLOAD folder)
            response_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_ai_response.txt")
            with open(response_file, 'w', encoding='utf-8') as f:
                f.write(ai_response)
            print(f"💾 Saved AI response: {len(ai_response)} chars to {response_file}")
            
            processing_status[session_id] = {
                'status': 'processing',
                'message': 'Generating professional documents...',
                'percentage': 80
            }
            
            # Initialize document generator with customization
            doc_generator = ImprovedDocumentGenerator(
                highlight_color=customization.get('highlight_color', 'BFBFBF'),
                font_family=customization.get('font_family', 'Calibri'),
                base_font_size=float(customization.get('font_size', 10.0))
            )
            
            # Generate documents (in GENERATED_DOCUMENTS folder) WITHOUT passing customization again
            doc_files = doc_generator.generate_all_documents(
                ai_response=ai_response,
                session_id=session_id,
                output_folder=app.config['GENERATED_FOLDER'],
                format='docx',
                merge=False
            )
            
            if not doc_files:
                processing_status[session_id] = {
                    'status': 'error',
                    'message': 'Document generation failed - no files created',
                    'percentage': 0
                }
                return None
            
            # Extract email content from AI response - USING FIXED FUNCTION
            email_content = extract_email_content_from_response(ai_response)
            
            # Save email content to file for reference
            email_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_email_content.json")
            with open(email_file, 'w', encoding='utf-8') as f:
                json.dump(email_content, f, indent=2)
            
            print(f"📧 Extracted AI-generated email content: Subject='{email_content['subject']}'")
            print(f"📧 Email body preview: {email_content['body'][:200]}...")
            
            # Check for required files in GENERATED_DOCUMENTS folder
            cv_file = doc_files.get('cv_docx')
            cover_file = doc_files.get('cover_docx')
            
            if not cv_file:
                print("❌ CV file not generated")
                processing_status[session_id] = {
                    'status': 'error',
                    'message': 'CV generation failed',
                    'percentage': 0
                }
                return None
            
            if not cover_file:
                print("❌ Cover Letter file not generated")
                processing_status[session_id] = {
                    'status': 'error',
                    'message': 'Cover Letter generation failed',
                    'percentage': 0
                }
                return None
            
            # Verify files exist in GENERATED_DOCUMENTS folder
            if not os.path.exists(cv_file):
                print(f"❌ CV file doesn't exist: {cv_file}")
                processing_status[session_id] = {
                    'status': 'error',
                    'message': 'CV file not found after generation',
                    'percentage': 0
                }
                return None
            
            if not os.path.exists(cover_file):
                print(f"❌ Cover Letter file doesn't exist: {cover_file}")
                processing_status[session_id] = {
                    'status': 'error',
                    'message': 'Cover Letter file not found after generation',
                    'percentage': 0
                }
                return None
            
            print(f"✅ CV file verified in generated_documents folder: {cv_file}")
            print(f"✅ Cover Letter file verified in generated_documents folder: {cover_file}")
            
            # Update paths for download URLs
            cv_filename = os.path.basename(cv_file)
            cover_filename = os.path.basename(cover_file)
            
            processing_status[session_id] = {
                'status': 'completed',
                'message': 'Complete! Your documents are ready for download.',
                'percentage': 100,
                'cv_url': f'/download/{session_id}/cv',
                'cover_url': f'/download/{session_id}/cover',
                'cv_filename': cv_filename,
                'cover_filename': cover_filename,
                'customization': customization,
                'email_content': email_content  # Add AI-generated email content
            }
            
            return {
                'doc_files': doc_files,
                'session_id': session_id,
                'customization': customization,
                'email_content': email_content  # Return email content
            }
            
        except Exception as e:
            print(f"❌ Processing error: {e}")
            import traceback
            traceback.print_exc()
            processing_status[session_id] = {
                'status': 'error',
                'message': f'Error: {str(e)}',
                'percentage': 0
            }
            return None
    
    def regenerate_with_feedback(self, session_id: str, cv_content: str, 
                                job_info: str, customization: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Regenerate documents with user feedback"""
        global deepseek_processor
        
        try:
            # Update processing status
            processing_status[session_id] = {
                'status': 'processing',
                'message': 'Processing your feedback...',
                'percentage': 20
            }
            
            # Get user feedback
            cv_feedback = customization.get('cv_feedback', '')
            cover_feedback = customization.get('cover_feedback', '')
            email_feedback = customization.get('email_feedback', '')
            
            print(f"📝 User feedback - CV: {len(cv_feedback)} chars, Cover: {len(cover_feedback)} chars, Email: {len(email_feedback)} chars")
            
            # Create enhanced prompt with feedback
            comprehensive_prompt = self.prompt_engineer.get_enhanced_prompt(
                cv_content, job_info, customization
            )
            
            # Save new prompt for debugging
            debug_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_feedback_prompt.txt")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(comprehensive_prompt)
            print(f"💾 Saved feedback prompt: {len(comprehensive_prompt)} chars to {debug_file}")
            
            processing_status[session_id] = {
                'status': 'processing',
                'message': 'Sending to AI with your feedback...',
                'percentage': 40
            }
            
            # Get AI response
            if deepseek_processor:
                ai_response = deepseek_processor.get_comprehensive_response(comprehensive_prompt)
            else:
                processing_status[session_id] = {
                    'status': 'error',
                    'message': 'DeepSeek processor not available',
                    'percentage': 0
                }
                return None
            
            if not ai_response:
                processing_status[session_id] = {
                    'status': 'error',
                    'message': 'Failed to get AI response',
                    'percentage': 0
                }
                return None
            
            # Save AI response
            response_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_feedback_response.txt")
            with open(response_file, 'w', encoding='utf-8') as f:
                f.write(ai_response)
            print(f"💾 Saved AI feedback response: {len(ai_response)} chars")
            
            processing_status[session_id] = {
                'status': 'processing',
                'message': 'Generating improved documents...',
                'percentage': 80
            }
            
            # Generate documents with customization
            doc_generator = ImprovedDocumentGenerator(
                highlight_color=customization.get('highlight_color', 'BFBFBF'),
                font_family=customization.get('font_family', 'Calibri'),
                base_font_size=float(customization.get('font_size', 10.0))
            )
            
            doc_files = doc_generator.generate_all_documents(
                ai_response=ai_response,
                session_id=session_id,
                output_folder=app.config['GENERATED_FOLDER'],
                format='docx',
                merge=False
            )
            
            # Extract email content from AI response - USING FIXED FUNCTION
            email_content = extract_email_content_from_response(ai_response)
            
            if not doc_files:
                processing_status[session_id] = {
                    'status': 'error',
                    'message': 'Document regeneration failed',
                    'percentage': 0
                }
                return None
            
            # Check for required files
            cv_file = doc_files.get('cv_docx')
            cover_file = doc_files.get('cover_docx')
            
            if not cv_file or not os.path.exists(cv_file):
                processing_status[session_id] = {
                    'status': 'error',
                    'message': 'CV regeneration failed',
                    'percentage': 0
                }
                return None
            
            if not cover_file or not os.path.exists(cover_file):
                processing_status[session_id] = {
                    'status': 'error',
                    'message': 'Cover Letter regeneration failed',
                    'percentage': 0
                }
                return None
            
            # Update processing status
            cv_filename = os.path.basename(cv_file)
            cover_filename = os.path.basename(cover_file)
            
            processing_status[session_id] = {
                'status': 'completed',
                'message': 'Complete! Documents regenerated with your feedback.',
                'percentage': 100,
                'cv_url': f'/download/{session_id}/cv',
                'cover_url': f'/download/{session_id}/cover',
                'cv_filename': cv_filename,
                'cover_filename': cover_filename,
                'customization': customization,
                'email_content': email_content  # Add regenerated email content
            }
            
            return {
                'doc_files': doc_files,
                'session_id': session_id,
                'customization': customization,
                'email_content': email_content
            }
            
        except Exception as e:
            print(f"❌ Regeneration error: {e}")
            import traceback
            traceback.print_exc()
            processing_status[session_id] = {
                'status': 'error',
                'message': f'Error: {str(e)}',
                'percentage': 0
            }
            return None
    
    def _initialize_deepseek(self) -> bool:
        """Initialize DeepSeek processor"""
        global deepseek_processor
        try:
            deepseek_processor = DeepSeekAutomation()
            if deepseek_processor.setup_chrome() and deepseek_processor.wait_for_deepseek_load():
                print("✅ Global DeepSeek processor initialized successfully")
                return True
            else:
                print("❌ Failed to initialize global DeepSeek processor")
                return False
        except Exception as e:
            print(f"❌ Error initializing global processor: {e}")
            return False


# ==================== GLOBAL INITIALIZATION ====================

def initialize_global_processor() -> bool:
    """Initialize global DeepSeek processor"""
    global deepseek_processor
    try:
        deepseek_processor = DeepSeekAutomation()
        if deepseek_processor.setup_chrome() and deepseek_processor.wait_for_deepseek_load():
            print("✅ Global DeepSeek processor initialized successfully")
            return True
        else:
            print("❌ Failed to initialize global DeepSeek processor")
            return False
    except Exception as e:
        print(f"❌ Error initializing global processor: {e}")
        return False

def cleanup_global_processor() -> None:
    """Cleanup global processor on exit"""
    global deepseek_processor
    if deepseek_processor:
        deepseek_processor.close()

atexit.register(cleanup_global_processor)


# ==================== HELPER FUNCTIONS ====================

def _get_file_extension(filename: Optional[str]) -> str:
    """Safely get file extension"""
    if filename:
        return os.path.splitext(filename)[1] or ''
    return ''

def _validate_customization(customization: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize customization options"""
    validated: Dict[str, Any] = {
        'highlight_color': 'BFBFBF',
        'font_family': 'Calibri',
        'font_size': 10.0
    }
    
    # Validate highlight color
    highlight_color = customization.get('highlight_color', '')
    if isinstance(highlight_color, str):
        highlight_color = highlight_color.strip().upper()
        valid_colors = ['BFBFBF', 'D4EDFF', 'FFE5D4', 'D4FFE5', 'FFD4E5', 'FFFACD', 'E5D4FF']
        if highlight_color in valid_colors:
            validated['highlight_color'] = highlight_color
    
    # Validate font family
    font_family = customization.get('font_family', '')
    if isinstance(font_family, str):
        font_family = font_family.strip()
        valid_fonts = ['Calibri', 'Arial', 'Times New Roman', 'Georgia', 'Verdana', 'Tahoma']
        if font_family in valid_fonts:
            validated['font_family'] = font_family
    
    # Validate font size
    font_size = customization.get('font_size', 10.0)
    try:
        if isinstance(font_size, (int, float, str)):
            font_size_float = float(font_size)
            if 9.0 <= font_size_float <= 12.0:
                validated['font_size'] = font_size_float
    except (ValueError, TypeError):
        pass
    
    # Add feedback if present
    cv_feedback = customization.get('cv_feedback', '')
    cover_feedback = customization.get('cover_feedback', '')
    email_feedback = customization.get('email_feedback', '')
    
    if cv_feedback:
        validated['cv_feedback'] = cv_feedback
    if cover_feedback:
        validated['cover_feedback'] = cover_feedback
    if email_feedback:
        validated['email_feedback'] = email_feedback
    
    return validated


def log_email_sent(session_id: str, recipient: str, subject: str, result: Dict[str, Any]) -> None:
    """Log email sending activity"""
    log_file = os.path.join(app.config['UPLOAD_FOLDER'], 'email_log.json')
    
    try:
        log_data: List[Dict[str, Any]] = []
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                try:
                    log_data = json.load(f)
                except json.JSONDecodeError:
                    log_data = []
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'recipient': recipient,
            'subject': subject,
            'recipient_count': result.get('recipient_count', 0),
            'attachment_count': result.get('attachment_count', 0),
            'success': result.get('success', False)
        }
        
        log_data.append(log_entry)
        
        # Keep only last 100 entries
        if len(log_data) > 100:
            log_data = log_data[-100:]
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
            
    except Exception as e:
        print(f"⚠️ Failed to log email: {e}")


# ==================== SAFE TEXT PROCESSING FUNCTIONS ====================

def safe_process_text(text: Optional[str]) -> Dict[str, Any]:
    """Process text safely handling None values - FIX for lines 2065-2068 errors"""
    if not text:
        return {
            'text': '',
            'length': 0,
            'has_content': False,
            'lines': 0,
            'words': 0
        }
    
    # Now text is guaranteed to be a string, not None
    text_str = str(text)
    lines = text_str.split('\n')
    words = text_str.split()
    
    return {
        'text': text_str,
        'length': len(text_str),  # No more TypeScript error
        'has_content': len(text_str.strip()) > 0,
        'lines': len(lines),
        'words': len(words)
    }


# ==================== GLOBAL PROCESSOR INSTANCE ====================

# Initialize processor with document processor
processor = None
if DOCUMENT_PROCESSOR_AVAILABLE and your_document_processor:
    try:
        processor = JobApplicationProcessor(document_processor=your_document_processor)
        print("✅ JobApplicationProcessor initialized successfully with document_processor.py")
    except Exception as e:
        print(f"❌ Failed to initialize JobApplicationProcessor: {e}")
        processor = None
else:
    print("❌ Cannot initialize processor without document_processor.py")


# ==================== FLASK ROUTES ====================

@app.before_request
def initialize_app() -> None:
    """Initialize the application before first request"""
    global app_initialized, processor
    if not app_initialized:
        print("🚀 Initializing Job Application Assistant...")
        print("⏳ Starting DeepSeek connection (this may take 10-15 seconds)...")
        if not initialize_global_processor():
            print("⚠️ Warning: Could not initialize DeepSeek processor on startup")
        else:
            print("✅ System ready!")
        app_initialized = True

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads and start processing using your document_processor.py"""
    global processor
    
    if not processor:
        return jsonify({'error': 'Document processor not available. Please ensure document_processor.py is in the same directory.'}), 500
    
    try:
        session_id = str(uuid.uuid4())
        
        cv_file = request.files.get('cv')
        job_file = request.files.get('job_description')
        job_link = request.form.get('job_link', '')
        
        # Get customization options
        customization = {
            'highlight_color': request.form.get('highlight_color', 'BFBFBF'),
            'font_family': request.form.get('font_family', 'Calibri'),
            'font_size': request.form.get('font_size', 10.0)
        }
        
        # Validate customization
        customization = _validate_customization(customization)
        
        # Validate CV file
        if not cv_file:
            return jsonify({'error': 'CV file is required'}), 400
        
        if cv_file.filename == '':
            return jsonify({'error': 'No CV file selected'}), 400
        
        # Save CV file to UPLOAD folder
        cv_filename = f"{session_id}_cv{_get_file_extension(cv_file.filename)}"
        cv_path = os.path.join(app.config['UPLOAD_FOLDER'], cv_filename)
        cv_file.save(cv_path)
        
        # Extract CV content using your document_processor.py
        cv_content = processor.document_processor.extract_text_from_file(cv_path)
        
        if not cv_content or not processor.document_processor.verify_extraction_completeness(cv_content, 'cv'):
            error_msg = 'Could not extract sufficient text from CV. Please ensure your CV is readable and try again.'
            print(f"❌ {error_msg}")
            return jsonify({'error': error_msg}), 400
        
        # Process job information
        job_info = ""
        
        # Process job description file if provided
        if job_file and job_file.filename != '':
            job_filename = f"{session_id}_job{_get_file_extension(job_file.filename)}"
            job_path = os.path.join(app.config['UPLOAD_FOLDER'], job_filename)
            job_file.save(job_path)
            
            job_info = processor.document_processor.extract_text_from_file(job_path)
            if not job_info or not processor.document_processor.verify_extraction_completeness(job_info, 'job'):
                error_msg = 'Could not extract sufficient text from job description file. Please ensure the file is readable.'
                print(f"❌ {error_msg}")
                return jsonify({'error': error_msg}), 400
        
        # Process job link if provided and no file was provided
        elif job_link and job_link.strip():
            print(f"🔗 Processing job link: {job_link}")
            
            # Extract text from URL using your document_processor.py
            job_info = processor.document_processor.extract_text_from_url(job_link)
            
            if not job_info or not processor.document_processor.verify_extraction_completeness(job_info, 'job'):
                print(f"⚠️ URL extraction may be incomplete, using URL as fallback")
                job_info = f"Job URL: {job_link}\n\nNote: Could not fully extract content from the URL. Please review the job posting directly at: {job_link}"
        
        if not job_info:
            return jsonify({'error': 'Please provide either a job description file or URL'}), 400
        
        # Save job info for debugging (in UPLOAD folder)
        job_info_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_job_info.txt")
        with open(job_info_file, 'w', encoding='utf-8') as f:
            f.write(job_info)
        
        print(f"✅ All content extracted successfully using document_processor.py:")
        print(f"   - CV: {len(cv_content)} characters")
        print(f"   - Job Info: {len(job_info)} characters")
        
        # Start processing in background thread
        thread = threading.Thread(
            target=processor.process_job_application,
            args=(session_id, cv_content, job_info, customization)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'session_id': session_id,
            'message': 'Processing started successfully',
            'customization': customization,
            'email_content': {
                'subject': 'AI is generating personalized email content...',
                'body': 'DeepSeek AI is creating a tailored email based on your CV and job description. Please wait for processing to complete.'
            }
        })
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/progress/<session_id>')
def get_progress(session_id: str):
    """Get processing progress"""
    progress = processing_status.get(session_id, {
        'status': 'unknown',
        'message': 'Session not found',
        'percentage': 0
    })
    return jsonify(progress)

@app.route('/download/<session_id>/<document_type>')
def download_document(session_id: str, document_type: str):
    """Download generated documents from GENERATED_DOCUMENTS folder"""
    try:
        # Determine the correct filename based on document type
        if document_type == 'cv':
            # Try multiple possible filenames
            possible_filenames = [
                f"{session_id}_cv_docx.docx",
                f"{session_id}_cv.docx",
                f"{session_id}_cv_docx",
                f"{session_id}_cv"
            ]
            download_name = "Optimized_CV.docx"
        elif document_type == 'cover':
            possible_filenames = [
                f"{session_id}_cover_docx.docx",
                f"{session_id}_cover_letter.docx",
                f"{session_id}_cover_docx",
                f"{session_id}_cover_letter"
            ]
            download_name = "Cover_Letter.docx"
        else:
            return jsonify({'error': 'Invalid document type'}), 400
        
        # Look for the file in GENERATED_DOCUMENTS folder
        generated_folder = app.config['GENERATED_FOLDER']
        file_path = None
        
        for filename in possible_filenames:
            # Try with .docx extension if not already present
            if not filename.endswith('.docx'):
                filename_with_ext = filename + '.docx'
                test_path = os.path.join(generated_folder, filename_with_ext)
                if os.path.exists(test_path):
                    file_path = test_path
                    break
            
            # Try as-is
            test_path = os.path.join(generated_folder, filename)
            if os.path.exists(test_path):
                file_path = test_path
                break
        
        if not file_path:
            print(f"❌ File not found in {generated_folder}")
            # List files for debugging
            print(f"📁 Files in {generated_folder}:")
            if os.path.exists(generated_folder):
                for f in os.listdir(generated_folder):
                    if session_id in f:
                        print(f"   - {f}")
            return jsonify({'error': f'File not found for session {session_id}'}), 404
        
        print(f"✅ Serving file from generated_documents: {file_path}")
        return send_file(file_path, as_attachment=True, download_name=download_name)
        
    except Exception as e:
        print(f"❌ Download error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/get_document_content/<session_id>')
def get_document_content(session_id: str):
    """Get document content for preview using your document_processor.py"""
    global processor
    
    if not processor:
        return jsonify({'success': False, 'error': 'Document processor not available'})
    
    try:
        generated_folder = app.config['GENERATED_FOLDER']
        
        # Find CV and cover letter files
        cv_content = ""
        cover_content = ""
        
        for filename in os.listdir(generated_folder):
            if session_id in filename:
                file_path = os.path.join(generated_folder, filename)
                if os.path.exists(file_path):
                    # Extract text using your document_processor.py
                    content = processor.document_processor.extract_text_from_file(file_path)
                    
                    if 'cv' in filename.lower():
                        cv_content = content or ""
                    elif 'cover' in filename.lower():
                        cover_content = content or ""
        
        # Use the safe processing function to handle None values
        cv_processed = safe_process_text(cv_content)
        cover_processed = safe_process_text(cover_content)
        
        if not cv_processed['has_content'] and not cover_processed['has_content']:
            return jsonify({'success': False, 'error': 'No document content found'})
        
        return jsonify({
            'success': True,
            'cv_content': cv_processed['text'][:5000] + "..." if cv_processed['length'] > 5000 else cv_processed['text'],
            'cover_content': cover_processed['text'][:3000] + "..." if cover_processed['length'] > 3000 else cover_processed['text'],
            'cv_length': cv_processed['length'],
            'cover_length': cover_processed['length']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/regenerate', methods=['POST'])
def regenerate_documents():
    """Regenerate documents with user feedback using your document_processor.py"""
    global processor
    
    if not processor:
        return jsonify({'error': 'Document processor not available'}), 500
    
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        original_session_id = data.get('session_id')
        cv_feedback = data.get('cv_feedback', '')
        cover_feedback = data.get('cover_feedback', '')
        email_feedback = data.get('email_feedback', '')
        
        if not original_session_id:
            return jsonify({'error': 'Session ID is required'}), 400
        
        # Check if we have original session files
        upload_folder = app.config['UPLOAD_FOLDER']
        
        # Find original CV and job info
        cv_file = None
        job_file = None
        
        for filename in os.listdir(upload_folder):
            if original_session_id in filename:
                if 'cv' in filename.lower() and not ('prompt' in filename.lower() or 'response' in filename.lower()):
                    cv_file = os.path.join(upload_folder, filename)
                elif 'job_info' in filename.lower():
                    job_file = os.path.join(upload_folder, filename)
        
        if not cv_file:
            return jsonify({'error': 'Original CV not found'}), 404
        
        # Extract CV content using your document_processor.py
        cv_content = processor.document_processor.extract_text_from_file(cv_file)
        
        # Extract job info
        job_info = ""
        if job_file and os.path.exists(job_file):
            with open(job_file, 'r', encoding='utf-8') as f:
                job_info = f.read()
        
        # Find customization from original processing
        customization = {}
        if original_session_id in processing_status:
            customization = processing_status[original_session_id].get('customization', {})
        
        # Add feedback to customization
        if cv_feedback:
            customization['cv_feedback'] = cv_feedback
        if cover_feedback:
            customization['cover_feedback'] = cover_feedback
        if email_feedback:
            customization['email_feedback'] = email_feedback
        
        # Create new session for regenerated documents
        new_session_id = f"{original_session_id}_regenerated_{int(time.time())}"
        
        # Start regeneration process
        thread = threading.Thread(
            target=processor.regenerate_with_feedback,
            args=(new_session_id, cv_content or "", job_info, customization)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'session_id': new_session_id,
            'message': 'Regeneration started with your feedback'
        })
        
    except Exception as e:
        print(f"❌ Regeneration error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/send_email', methods=['POST'])
def send_email():
    """Handle email sending with attachments"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Extract parameters
        session_id = data.get('session_id')
        recipient_email = data.get('recipient_email')
        cc_emails = data.get('cc_emails', '')
        bcc_emails = data.get('bcc_emails', '')
        subject = data.get('subject', 'Job Application')
        message = data.get('message', '')
        reply_to = data.get('reply_to', '')
        
        # Validate required fields
        if not session_id:
            return jsonify({'error': 'Session ID is required'}), 400
        if not recipient_email:
            return jsonify({'error': 'Recipient email is required'}), 400
        
        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, recipient_email):
            return jsonify({'error': 'Invalid recipient email format'}), 400
        
        # Parse CC and BCC emails
        cc_list = []
        bcc_list = []
        
        if cc_emails:
            cc_list = [email.strip() for email in cc_emails.split(',') if email.strip()]
            # Validate CC emails
            for email in cc_list:
                if not re.match(email_pattern, email):
                    return jsonify({'error': f'Invalid CC email format: {email}'}), 400
        
        if bcc_emails:
            bcc_list = [email.strip() for email in bcc_emails.split(',') if email.strip()]
            # Validate BCC emails
            for email in bcc_list:
                if not re.match(email_pattern, email):
                    return jsonify({'error': f'Invalid BCC email format: {email}'}), 400
        
        # Find generated documents for this session
        generated_folder = app.config['GENERATED_FOLDER']
        attachments = []
        
        # Look for DOCX files first (preferred)
        cv_file = None
        cover_file = None
        
        for filename in os.listdir(generated_folder):
            if session_id in filename:
                file_path = os.path.join(generated_folder, filename)
                if filename.endswith('.docx'):
                    if '_cv' in filename.lower() or 'cv_' in filename.lower():
                        cv_file = file_path
                    elif '_cover' in filename.lower() or 'cover_' in filename.lower():
                        cover_file = file_path
        
        # If not found as DOCX, look for any matching files
        if not cv_file or not cover_file:
            for filename in os.listdir(generated_folder):
                if session_id in filename:
                    file_path = os.path.join(generated_folder, filename)
                    if not cv_file and ('cv' in filename.lower() or 'resume' in filename.lower()):
                        cv_file = file_path
                    elif not cover_file and ('cover' in filename.lower() or 'letter' in filename.lower()):
                        cover_file = file_path
        
        if cv_file:
            attachments.append(cv_file)
        if cover_file:
            attachments.append(cover_file)
        
        if not attachments:
            return jsonify({'error': 'No documents found for this session. Please generate documents first.'}), 400
        
        print(f"📧 Sending email for session {session_id}")
        print(f"   To: {recipient_email}")
        print(f"   CC: {cc_list}")
        print(f"   BCC: {bcc_list}")
        print(f"   Attachments: {[os.path.basename(a) for a in attachments]}")
        
        # Default email body if not provided
        if not message:
            message = f"""Dear Hiring Manager,

Please find attached my CV and cover letter for your consideration.

I believe my qualifications and experience make me an excellent candidate for the position.

Thank you for your time and consideration.

Best regards,
Job Applicant"""
        
        # Send email using the global email service
        result = email_service.send_application_email(
            recipient_email=recipient_email,
            subject=subject,
            body=message,
            attachments=attachments,
            cc_emails=cc_list,
            bcc_emails=bcc_list,
            reply_to=reply_to
        )
        
        if result.get('success'):
            # Log successful email sending
            log_email_sent(session_id, recipient_email, subject, result)
            
            return jsonify({
                'success': True,
                'message': 'Email sent successfully',
                'details': {
                    'recipient_count': result.get('recipient_count', 0),
                    'attachment_count': result.get('attachment_count', 0),
                    'total_size': result.get('total_size_bytes', 0)
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to send email')
            }), 500
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/test_email', methods=['POST'])
def test_email():
    """Test email configuration with optional recipient"""
    try:
        data = request.json or {}
        test_recipient = data.get('recipient')
        
        print("🧪 Testing email configuration...")
        result = email_service.send_test_email(test_recipient)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': 'Test email sent successfully!',
                'details': result
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to send test email')
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate_email_content', methods=['POST'])
def generate_email_content():
    """Generate improved email content based on session data"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'error': 'Session ID required'}), 400
        
        # Check if we have AI-generated email content in processing status
        if session_id in processing_status and 'email_content' in processing_status[session_id]:
            email_content = processing_status[session_id]['email_content']
            return jsonify({
                'success': True,
                'subject': email_content.get('subject', 'Application for Position'),
                'body': email_content.get('body', 'Dear Hiring Manager,\n\nPlease find attached...')
            })
        
        # Fallback: try to read from saved email content file
        upload_folder = app.config['UPLOAD_FOLDER']
        email_file = os.path.join(upload_folder, f"{session_id}_email_content.json")
        
        if os.path.exists(email_file):
            with open(email_file, 'r', encoding='utf-8') as f:
                email_content = json.load(f)
            return jsonify({
                'success': True,
                'subject': email_content.get('subject', 'Application for Position'),
                'body': email_content.get('body', 'Dear Hiring Manager,\n\nPlease find attached...')
            })
        
        return jsonify({
            'success': False,
            'error': 'No AI-generated email content found for this session'
        })
        
    except Exception as e:
        print(f"❌ Error generating email content: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    global deepseek_processor, processor
    
    health_status = {
        'status': 'degraded' if not deepseek_processor or not deepseek_processor.keep_alive() else 'healthy',
        'deepseek': 'connected' if deepseek_processor and deepseek_processor.keep_alive() else 'disconnected',
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'generated_folder': app.config['GENERATED_FOLDER'],
        'upload_folder_exists': os.path.exists(app.config['UPLOAD_FOLDER']),
        'generated_folder_exists': os.path.exists(app.config['GENERATED_FOLDER']),
        'email_enabled': email_service.enabled,
        'email_sender': email_service.config.get('SENDER_EMAIL', 'Not configured'),
        'document_processor': 'available' if DOCUMENT_PROCESSOR_AVAILABLE else 'unavailable',
        'job_processor': 'initialized' if processor else 'failed',
        'document_processor_methods': 'FULLY INTEGRATED' if processor and processor.document_processor else 'NOT INTEGRATED'
    }
    
    return jsonify(health_status)

@app.route('/debug/<session_id>')
def debug_info(session_id: str):
    """Debug endpoint to see what files were generated"""
    debug_info: Dict[str, Any] = {
        'session_id': session_id,
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'generated_folder': app.config['GENERATED_FOLDER'],
        'upload_files': [],
        'generated_files': [],
        'processing_status': processing_status.get(session_id)
    }
    
    # Check UPLOAD folder
    upload_folder = app.config['UPLOAD_FOLDER']
    if os.path.exists(upload_folder):
        for f in os.listdir(upload_folder):
            if session_id in f:
                file_path = os.path.join(upload_folder, f)
                debug_info['upload_files'].append({
                    'name': f,
                    'path': file_path,
                    'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    'exists': os.path.exists(file_path)
                })
    
    # Check GENERATED_DOCUMENTS folder
    generated_folder = app.config['GENERATED_FOLDER']
    if os.path.exists(generated_folder):
        for f in os.listdir(generated_folder):
            if session_id in f:
                file_path = os.path.join(generated_folder, f)
                debug_info['generated_files'].append({
                    'name': f,
                    'path': file_path,
                    'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    'exists': os.path.exists(file_path)
                })
    
    return jsonify(debug_info)

@app.route('/cleanup/<session_id>', methods=['DELETE'])
def cleanup_session(session_id: str):
    """Clean up session files from both folders"""
    try:
        deleted_files: List[str] = []
        
        # Clean up UPLOAD folder
        upload_folder = app.config['UPLOAD_FOLDER']
        if os.path.exists(upload_folder):
            for f in os.listdir(upload_folder):
                if session_id in f:
                    file_path = os.path.join(upload_folder, f)
                    try:
                        os.remove(file_path)
                        deleted_files.append(f"uploads/{f}")
                    except Exception as e:
                        print(f"⚠️ Could not delete {file_path}: {e}")
        
        # Clean up GENERATED_DOCUMENTS folder
        generated_folder = app.config['GENERATED_FOLDER']
        if os.path.exists(generated_folder):
            for f in os.listdir(generated_folder):
                if session_id in f:
                    file_path = os.path.join(generated_folder, f)
                    try:
                        os.remove(file_path)
                        deleted_files.append(f"generated_documents/{f}")
                    except Exception as e:
                        print(f"⚠️ Could not delete {file_path}: {e}")
        
        # Remove from processing status
        if session_id in processing_status:
            del processing_status[session_id]
        
        return jsonify({
            'message': f'Cleaned up {len(deleted_files)} files',
            'deleted_files': deleted_files
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== MAIN EXECUTION ====================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 AI JOB APPLICATION ASSISTANT WITH DOCUMENT REGENERATION")
    print("=" * 60)
    print(f"📁 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"📁 Generated folder: {app.config['GENERATED_FOLDER']}")
    print(f"📧 Email enabled: {email_service.enabled}")
    if email_service.enabled:
        print(f"📧 Email sender: {email_service.config.get('SENDER_EMAIL')}")
    print(f"📄 Document processor: {'✅ Available' if DOCUMENT_PROCESSOR_AVAILABLE else '❌ Unavailable'}")
    print(f"🤖 Document processor methods: {'✅ FULLY INTEGRATED' if processor and processor.document_processor else '❌ NOT INTEGRATED'}")
    print("=" * 60)
    print("Folder status:")
    print(f"  - UPLOAD folder exists: {os.path.exists(app.config['UPLOAD_FOLDER'])}")
    print(f"  - GENERATED folder exists: {os.path.exists(app.config['GENERATED_FOLDER'])}")
    print("=" * 60)
    print("Features:")
    print("  ✅ Document generation with DeepSeek AI")
    print("  ✅ AI-generated email content (subject & body)")
    print("  ✅ User feedback and document regeneration")
    print("  ✅ Email submission with attachments")
    print("  ✅ Document preview in browser")
    print("  ✅ Comprehensive document processing using document_processor.py")
    print("=" * 60)
    print("Document Processor Integration Points:")
    print("  1. CV text extraction from PDF/DOCX/Images/TXT")
    print("  2. Job description extraction from files")
    print("  3. Job posting extraction from URLs")
    print("  4. Generated document text extraction for preview")
    print("  5. Text verification and completeness checking")
    print("=" * 60)
    print("Starting server...")
    print("Open your browser to: http://localhost:5000")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)