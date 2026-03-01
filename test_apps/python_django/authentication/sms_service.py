import requests
import os
from django.conf import settings


class SMSService:
    def __init__(self):
        self.api_key = getattr(settings, 'SMS_API_KEY', '')
        self.api_url = getattr(settings, 'SMS_API_URL', 'https://api.sms-service.com/send')
    
    def send_otp(self, phone_number, otp):
        """Send OTP via SMS service"""
        message = f"Your verification code is: {otp}. Valid for 5 minutes."
        
        # For development/testing, we'll use a mock service
        if getattr(settings, 'SMS_DEBUG', True):
            print(f"SMS DEBUG: Would send to {phone_number}: {message}")
            return True
        
        # Production SMS service integration
        try:
            payload = {
                'api_key': self.api_key,
                'to': phone_number,
                'message': message
            }
            response = requests.post(self.api_url, json=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"SMS sending failed: {e}")
            return False