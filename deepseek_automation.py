#deepseek_automation.py
import subprocess
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Optional
import re
import pyperclip


class DeepSeekAutomation:
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.is_connected = False
    
    def setup_chrome(self) -> bool:
        """One-click Chrome setup"""
        print("🛠️  Setting up Chrome for automation...")
        
        # Kill Chrome
        print("🔴 Closing Chrome...")
        os.system("taskkill /f /im chrome.exe 2>nul")
        time.sleep(2)
        
        # Start Chrome with debugging
        print("🟢 Starting Chrome with debugging...")
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        
        subprocess.Popen([
            chrome_path,
            "--remote-debugging-port=9222",
            "--user-data-dir=C:\\ChromeDebug",
            "https://chat.deepseek.com"
        ])
        
        print("✅ Chrome started!")
        print("⏳ Waiting for Chrome to initialize...")
        time.sleep(8)
        
        # Connect to Chrome
        return self._connect_to_chrome()
    
    def _connect_to_chrome(self) -> bool:
        """Connect to the running Chrome instance"""
        try:
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)
            self.is_connected = True
            print("✅ Connected to Chrome!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to Chrome: {e}")
            self.is_connected = False
            return False
    
    def _ensure_driver_ready(self) -> bool:
        """Ensure driver and wait are initialized"""
        if not self.is_connected or self.driver is None or self.wait is None:
            print("❌ Driver not initialized. Please call setup_chrome() first.")
            return False
        return True
    
    def wait_for_deepseek_load(self) -> bool:
        """Wait for DeepSeek to fully load"""
        if not self._ensure_driver_ready():
            return False
            
        print("⏳ Waiting for DeepSeek to load...")
        time.sleep(5)
        
        try:
            if self.wait:
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            print("✅ DeepSeek page loaded!")
            return True
        except Exception as e:
            print(f"⚠️ Page load warning: {e}")
            return False
    
    def find_input_element(self):
        """Find the main chat input element"""
        if not self._ensure_driver_ready():
            return None
            
        print("🔍 Looking for main chat input...")
        
        # More specific selectors for DeepSeek's main chat input
        selectors = [
            "textarea[placeholder*='message']",
            "textarea[placeholder*='Message']",
            "textarea[placeholder*='chat']", 
            "textarea[placeholder*='Chat']",
            "textarea[data-id]",
            "textarea.focus-visible",
            "textarea",
            "[contenteditable='true'][role='textbox']",
            "[contenteditable='true']",
            "[role='textbox']",
        ]
        
        for selector in selectors:
            try:
                if self.driver:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            print(f"✅ Found input element with selector: {selector}")
                            return element
            except Exception as e:
                continue
        
        print("❌ Could not find main chat input element")
        return None

    def debug_input_field(self, input_element):
        """Debug information about the input field"""
        try:
            print("🔍 DEBUG Input Field Information:")
            print(f"   Tag: {input_element.tag_name}")
            print(f"   Type: {input_element.get_attribute('type')}")
            print(f"   Placeholder: {input_element.get_attribute('placeholder')}")
            print(f"   Value: {input_element.get_attribute('value')}")
            print(f"   Text: {input_element.text}")
            print(f"   Is displayed: {input_element.is_displayed()}")
            print(f"   Is enabled: {input_element.is_enabled()}")
        except Exception as e:
            print(f"❌ Debug failed: {e}")

    def send_via_clipboard(self, prompt: str) -> bool:
        """Use clipboard paste for atomic input - PRIMARY METHOD"""
        input_element = self.find_input_element()
        if not input_element:
            return False
        
        print(f"📋 Using clipboard method for {len(prompt)} characters...")
        
        try:
            # Copy to clipboard
            pyperclip.copy(prompt)
            time.sleep(1)  # Ensure clipboard is ready
            
            # Focus and clear the input field
            input_element.click()
            time.sleep(0.5)
            
            # Clear any existing content
            input_element.clear()
            time.sleep(0.5)
            
            # Paste with Ctrl+V
            input_element.send_keys(Keys.CONTROL + "v")
            time.sleep(3)  # Wait for paste to complete and process
            
            # Verify the content was pasted correctly
            current_value = input_element.get_attribute('value') or input_element.text or ""
            current_length = len(current_value)
            expected_length = len(prompt)
            
            print(f"📊 Clipboard verification: {current_length}/{expected_length} characters")
            
            if current_length >= expected_length * 0.9:  # 90% threshold
                print("✅ Clipboard paste successful - sending to AI...")
                input_element.send_keys(Keys.RETURN)
                return True
            else:
                print(f"❌ Clipboard paste incomplete: {current_length} vs {expected_length}")
                return False
                
        except Exception as e:
            print(f"❌ Clipboard method failed: {e}")
            return False

    def send_prompt_fallback(self, prompt: str) -> bool:
        """Fallback method if clipboard fails"""
        input_element = self.find_input_element()
        if not input_element:
            return False
        
        print("🔄 Using fallback method...")
        
        try:
            # Clear and focus
            input_element.clear()
            input_element.click()
            time.sleep(1)
            
            # Send keys with minimal delays (larger chunks)
            chunk_size = 2000
            for i in range(0, len(prompt), chunk_size):
                chunk = prompt[i:i+chunk_size]
                input_element.send_keys(chunk)
                # Very small delay to prevent browser overload
                if i % 4000 == 0 and i > 0:
                    time.sleep(0.1)
            
            time.sleep(2)  # Final processing time
            
            # Verify
            current_value = input_element.get_attribute('value') or input_element.text or ""
            if len(current_value) >= len(prompt) * 0.8:
                print("✅ Fallback method successful")
                input_element.send_keys(Keys.RETURN)
                return True
                
        except Exception as e:
            print(f"❌ Fallback method failed: {e}")
        
        return False

    def send_complete_prompt(self, prompt: str) -> bool:
        """Send the entire prompt using clipboard method with fallback"""
        if not self._ensure_driver_ready():
            return False
            
        prompt_length = len(prompt) if prompt else 0
        print(f"💬 Sending complete prompt ({prompt_length} characters)...")
        
        # Clean the prompt
        clean_prompt = self._clean_text_for_chromedriver(prompt)
        
        # Try clipboard method first (most reliable)
        if self.send_via_clipboard(clean_prompt):
            return True
        
        # If clipboard fails, try fallback
        print("🔄 Clipboard failed, trying fallback...")
        return self.send_prompt_fallback(clean_prompt)

    def _clean_text_for_chromedriver(self, text: str) -> str:
        """Clean text for ChromeDriver"""
        if not text:
            return ""
        
        text_length = len(text) if text else 0
        print(f"🔧 Cleaning text: {text_length} characters")
        
        # Remove problematic Unicode characters
        cleaned = re.sub(r'[^\x00-\xFFFF]', '', text)
        problematic_chars = ['\u2028', '\u2029', '\u0085']
        for char in problematic_chars:
            cleaned = cleaned.replace(char, ' ')
        
        cleaned_length = len(cleaned) if cleaned else 0
        print(f"✅ Cleaned text: {cleaned_length} characters remaining")
        return cleaned
    
    def wait_for_response_complete(self, timeout: int = 400) -> bool:
        """Wait for the AI response to complete"""
        if not self._ensure_driver_ready():
            return False
            
        print("⏳ Waiting for comprehensive AI response (this may take 3-5 minutes)...")
        start_time = time.time()
        last_response_length = 0
        stable_count = 0
        check_interval = 5
        
        while time.time() - start_time < timeout:
            try:
                current_response = self._get_raw_page_text()
                current_length = len(current_response) if current_response else 0
                
                if self._is_deepseek_typing():
                    elapsed = int(time.time() - start_time)
                    print(f"🤖 DeepSeek is generating... ({elapsed}s elapsed, {current_length} chars)")
                    stable_count = 0
                    last_response_length = current_length
                    time.sleep(check_interval)
                    continue
                
                if current_length == last_response_length and current_length > 1000:
                    stable_count += 1
                    print(f"✅ Response stable ({stable_count}/6) - {current_length} chars")
                else:
                    stable_count = 0
                    last_response_length = current_length
                    if current_length > 0:
                        print(f"📈 Response growing: {current_length} chars")
                
                if stable_count >= 6:
                    print("✅ Response complete and stable!")
                    return True
                
                time.sleep(check_interval)
                
            except Exception as e:
                print(f"⚠️ Error waiting for response: {e}")
                time.sleep(check_interval)
        
        print("⚠️ Response wait timeout reached, proceeding with current content")
        return True
    
    def _is_deepseek_typing(self) -> bool:
        """Check if DeepSeek is typing"""
        if not self._ensure_driver_ready():
            return False
            
        typing_indicators = [
            "[class*='typing']",
            "[class*='thinking']",
            "[class*='loading']",
            "[class*='animate-pulse']",
            "[class*='cursor']",
            "[class*='generating']",
        ]
        
        for indicator in typing_indicators:
            try:
                if self.driver:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                    if elements and any(elem.is_displayed() for elem in elements):
                        return True
            except:
                continue
        return False

    def _get_raw_page_text(self) -> Optional[str]:
        """Get all text from the page"""
        if not self._ensure_driver_ready() or self.driver is None:
            return None
            
        try:
            return self.driver.find_element(By.TAG_NAME, "body").text
        except Exception as e:
            print(f"⚠️ Error getting page text: {e}")
            return None

    def _extract_complete_response(self, page_text: str) -> Optional[str]:
        """Extract the complete AI response from page text"""
        if not page_text:
            print("❌ No page text to extract from")
            return None
        
        page_text_length = len(page_text) if page_text else 0
        print(f"🔍 Analyzing response text ({page_text_length} chars)...")
        
        # Method 1: Find the LAST occurrence of the delimiters (most recent response)
        print("🔄 Searching for final delimiters...")
        
        # Split by possible delimiter variations
        delimiter_variations = [
            ('===OPTIMIZED_CV_START===', '===OPTIMIZED_CV_END==='),
            ('===COVER_LETTER_START===', '===COVER_LETTER_END==='),
            ('OPTIMIZED_CV_START', 'OPTIMIZED_CV_END'),
            ('COVER_LETTER_START', 'COVER_LETTER_END'),
        ]
        
        for cv_start, cv_end in delimiter_variations:
            for cover_start, cover_end in delimiter_variations:
                try:
                    # Find last occurrence of CV
                    cv_start_pos = page_text.rfind(cv_start)
                    cv_end_pos = page_text.rfind(cv_end)
                    
                    # Find last occurrence of cover letter
                    cover_start_pos = page_text.rfind(cover_start)
                    cover_end_pos = page_text.rfind(cover_end)
                    
                    if (cv_start_pos != -1 and cv_end_pos != -1 and cv_start_pos < cv_end_pos and
                        cover_start_pos != -1 and cover_end_pos != -1 and cover_start_pos < cover_end_pos):
                        
                        cv_content = page_text[cv_start_pos + len(cv_start):cv_end_pos].strip()
                        cover_content = page_text[cover_start_pos + len(cover_start):cover_end_pos].strip()
                        
                        cv_length = len(cv_content) if cv_content else 0
                        cover_length = len(cover_content) if cover_content else 0
                        
                        print(f"✅ Found documents with delimiters: {cv_start}...")
                        print(f"   CV: {cv_length} chars, Cover: {cover_length} chars")
                        
                        # Validate we have substantial content
                        if cv_length > 100 and cover_length > 100:
                            formatted_response = f"""===OPTIMIZED_CV_START===
{cv_content}
===OPTIMIZED_CV_END===

===COVER_LETTER_START===
{cover_content}
===COVER_LETTER_END==="""
                            return formatted_response
                except Exception as e:
                    continue
        
        # Method 2: Look for structured document patterns
        print("🔄 Searching for structured document patterns...")
        
        # Common CV section headers
        cv_headers = ['PROFESSIONAL SUMMARY', 'WORK EXPERIENCE', 'EDUCATION', 'SKILLS', 'CONTACT']
        cover_headers = ['Dear', 'Hiring Manager', 'Sincerely', 'Application for']
        
        lines = page_text.split('\n')
        cv_lines = []
        cover_lines = []
        current_section = None
        
        for line in lines:
            line_upper = line.upper().strip()
            
            # Check if this line starts a CV section
            if any(header in line_upper for header in cv_headers) and len(line_upper) < 100:
                current_section = 'cv'
                cv_lines.append(line)
                continue
                
            # Check if this line starts a cover letter section
            if any(header in line_upper for header in cover_headers) and len(line.strip()) > 10:
                current_section = 'cover'
                cover_lines.append(line)
                continue
            
            # Add content to current section
            if current_section == 'cv' and line.strip():
                cv_lines.append(line)
            elif current_section == 'cover' and line.strip():
                cover_lines.append(line)
        
        cv_content = '\n'.join(cv_lines).strip()
        cover_content = '\n'.join(cover_lines).strip()
        
        cv_length = len(cv_content) if cv_content else 0
        cover_length = len(cover_content) if cover_content else 0
        
        if cv_length > 500 and cover_length > 200:
            print(f"✅ Found structured documents - CV: {cv_length} chars, Cover: {cover_length} chars")
            
            formatted_response = f"""===OPTIMIZED_CV_START===
{cv_content}
===OPTIMIZED_CV_END===

===COVER_LETTER_START===
{cover_content}
===COVER_LETTER_END==="""
            return formatted_response
        
        print("❌ All extraction methods failed, returning raw text")
        return page_text

    def get_comprehensive_response(self, prompt: str) -> Optional[str]:
        """Send prompt and get comprehensive response with CV and cover letter"""
        if not self._ensure_driver_ready():
            print("❌ Driver not ready")
            return None
            
        print("=" * 60)
        print("🚀 STARTING COMPREHENSIVE AI PROCESSING")
        print("=" * 60)
        
        # Send complete prompt using clipboard method
        if not self.send_complete_prompt(prompt):
            print("❌ Failed to send prompt")
            return None
        
        print("\n⏳ Waiting for AI to generate both documents...")
        print("   This typically takes 2-3 minutes for quality results")
        print("=" * 60)
        
        # Wait for response
        self.wait_for_response_complete(timeout=400)
        
        # Final wait
        print("⏳ Finalizing response...")
        time.sleep(5)
        
        try:
            # Get page text
            page_text = self._get_raw_page_text()
            
            if not page_text:
                print("❌ Could not get page text")
                return None
            
            page_text_length = len(page_text) if page_text else 0
            print(f"📄 Retrieved page content: {page_text_length} characters")
            
            # Extract response
            response = self._extract_complete_response(page_text)
            
            response_length = len(response) if response else 0
            if response and response_length > 500:
                print("=" * 60)
                print("✅ COMPREHENSIVE RESPONSE RECEIVED")
                print(f"   Total length: {response_length} characters")
                print("=" * 60)
                return response
            else:
                print("⚠️ Response seems incomplete, returning raw page text")
                return page_text
            
        except Exception as e:
            print(f"❌ Error extracting response: {e}")
            return None

    def keep_alive(self) -> bool:
        """Keep the browser session alive"""
        try:
            if self._ensure_driver_ready() and self.driver:
                self.driver.current_url
                return True
        except:
            return False
        return False

    def close(self) -> None:
        """Close the browser connection"""
        if self.driver:
            try:
                self.driver.quit()
                self.is_connected = False
                print("🔴 Browser closed")
            except:
                pass