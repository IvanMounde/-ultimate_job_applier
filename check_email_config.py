#!/usr/bin/env python3
"""
Check Email Configuration Script
Run this to verify your .env configuration
"""

from dotenv import load_dotenv
import os
import sys
from typing import Optional

def check_config() -> bool:
    """Check email configuration from .env file"""
    load_dotenv()
    
    print("=" * 60)
    print("📧 CHECKING EMAIL CONFIGURATION")
    print("=" * 60)
    
    required_vars = [
        ('EMAIL_HOST_USER', 'Your Gmail address'),
        ('EMAIL_HOST_PASSWORD', 'Your Google App Password (16 characters)')
    ]
    
    optional_vars = [
        ('EMAIL_HOST', 'SMTP server (default: smtp.gmail.com)'),
        ('EMAIL_PORT', 'Port (default: 587)'),
        ('EMAIL_USE_TLS', 'Use TLS (default: True)'),
        ('EMAIL_USE_SSL', 'Use SSL (default: False)'),
        ('DEFAULT_FROM_EMAIL', 'Default from address'),
        ('EMAIL_SUBJECT_PREFIX', 'Email subject prefix'),
        ('MAX_EMAIL_SIZE_MB', 'Maximum email size in MB (default: 10)')
    ]
    
    print("\n🔍 Required Configuration:")
    missing = []
    for var, desc in required_vars:
        value = os.getenv(var)
        if value:
            # Mask password for security
            if 'PASSWORD' in var:
                print(f"   ✅ {var}: {desc} - {'*' * len(value)}")
            else:
                print(f"   ✅ {var}: {desc} - {value}")
        else:
            print(f"   ❌ {var}: {desc} - NOT SET")
            missing.append(var)
    
    print("\n📝 Optional Configuration:")
    for var, desc in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: {value}")
        else:
            print(f"   ⚠️  {var}: Using default")
    
    if missing:
        print(f"\n❌ Missing required configuration: {', '.join(missing)}")
        print("\n📋 Please add these to your .env file:")
        print("EMAIL_HOST_USER=your-email@gmail.com")
        print("EMAIL_HOST_PASSWORD=your-16-char-app-password")
        print("\n💡 Get your Google App Password from:")
        print("https://myaccount.google.com → Security → App passwords")
        return False
    
    # Test SMTP connection
    print("\n🔧 Testing SMTP connection...")
    
    # Import smtplib at module level or in a way that doesn't cause unbound variable issues
    try:
        import smtplib
        smtplib_available = True
    except ImportError:
        print("❌ smtplib module not available. Please install it:")
        print("   pip install 'python-dotenv[email]' or 'pip install secure-smtplib'")
        return False
    
    if not smtplib_available:
        return False
    
    try:
        # Get environment variables with defaults
        email_host: str = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
        email_port_str: Optional[str] = os.getenv('EMAIL_PORT')
        email_port: int = int(email_port_str) if email_port_str else 587
        
        email_user: Optional[str] = os.getenv('EMAIL_HOST_USER')
        email_pass: Optional[str] = os.getenv('EMAIL_HOST_PASSWORD')
        
        # Validate required variables are not None
        if not email_user or not email_pass:
            print("❌ Required email credentials are None")
            return False
        
        with smtplib.SMTP(email_host, email_port, timeout=10) as server:
            server.ehlo()
            
            # Check if TLS should be used
            use_tls_str: Optional[str] = os.getenv('EMAIL_USE_TLS')
            use_tls: bool = (use_tls_str or 'True').lower() == 'true'
            
            if use_tls:
                server.starttls()
                server.ehlo()
            
            # Now login with validated non-None values
            server.login(email_user, email_pass)
            server.quit()
        
        print("✅ SMTP connection successful!")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ SMTP authentication failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure you've enabled 2FA on your Google account")
        print("2. Generate a new 16-character app password for 'Mail'")
        print("3. Verify you're using the correct app password (not your regular password)")
        return False
    except Exception as e:
        print(f"❌ SMTP connection failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check your internet connection")
        print("2. Verify SMTP server and port are correct")
        print("3. Try enabling/disabling TLS in .env file")
        return False


if __name__ == "__main__":
    success = check_config()
    print("\n" + "=" * 60)
    if success:
        print("✅ Configuration check passed!")
        print("   You can now start your application with:")
        print("   python app.py")
    else:
        print("❌ Configuration check failed")
        sys.exit(1)