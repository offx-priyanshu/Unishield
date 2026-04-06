import requests
import json
from flask import current_app

class SMSService:
    @staticmethod
    def send_fast2sms(message, numbers):
        """Sends an SMS using Fast2SMS API."""
        url = "https://www.fast2sms.com/dev/bulkV2"
        api_key = current_app.config.get('FAST2SMS_API_KEY')
        
        if api_key == 'YOUR_FAST2_SMS_KEY':
            print(f"[MOCK SMS] Message: {message} To: {numbers}")
            return True, "Mock SMS sent"
            
        payload = {
            "message": message,
            "language": "english",
            "route": "p",
            "numbers": numbers
        }
        headers = {
            'authorization': api_key,
            'Content-Type': "application/x-www-form-urlencoded",
            'Cache-Control': "no-cache"
        }
        
        try:
            response = requests.post(url, data=payload, headers=headers)
            res_json = response.json()
            if res_json.get('return'):
                return True, "SMS sent successfully"
            else:
                return False, res_json.get('message', 'Failed to send SMS')
        except Exception as e:
            return False, str(e)

    @staticmethod
    def notify_exit(student_name, parent_phone, student_phone, destination, expected_return):
        message = f"SNOX ALERT: Student {student_name} has left campus for {destination}. Expected return: {expected_return}."
        numbers = f"{parent_phone},{student_phone}" if student_phone else parent_phone
        return SMSService.send_fast2sms(message, numbers)

    @staticmethod
    def notify_return(student_name, parent_phone, student_phone):
        message = f"SNOX ALERT: Student {student_name} has returned to campus safely."
        numbers = f"{parent_phone},{student_phone}" if student_phone else parent_phone
        return SMSService.send_fast2sms(message, numbers)

    @staticmethod
    def notify_overdue(student_name, parent_phone, student_phone, expected_return):
        message = f"SNOX CRITICAL: Student {student_name} is OVERDUE! Expected return was {expected_return}. Please contact immediately."
        numbers = f"{parent_phone},{student_phone}" if student_phone else parent_phone
        return SMSService.send_fast2sms(message, numbers)

    @staticmethod
    def notify_blacklisted(student_name, parent_phone, student_phone):
        message = f"SNOX ALERT: Student {student_name} has been BLACKLISTED due to multiple violations. Access blocked."
        numbers = f"{parent_phone},{student_phone}" if student_phone else parent_phone
        return SMSService.send_fast2sms(message, numbers)
