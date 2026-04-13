import requests
from flask import current_app
from datetime import datetime

class SMSService:
    @staticmethod
    def _get_config(key):
        from models.log import SMSConfig
        from models.db import db
        conf = SMSConfig.query.filter_by(key_name=key).first()
        return conf.value if conf else None

    @staticmethod
    def _log_sms(phone, template, message, provider, status, error=None):
        from models.log import SMSLog
        from models.db import db
        log = SMSLog(
            phone=phone,
            template=template,
            message=message,
            provider=provider,
            status=status,
            error_msg=error
        )
        db.session.add(log)
        db.session.commit()
        return log

    @staticmethod
    def send_sms(phone, message, template='CUSTOM'):
        """Main method with failover logic: Fast2SMS -> Twilio"""
        # Try Fast2SMS first
        success, res = SMSService.send_fast2sms(message, phone)
        if success:
            SMSService._log_sms(phone, template, message, 'fast2sms', 'DELIVERED')
            return True, "Sent via Fast2SMS"
        
        # If F2S fails, try Twilio
        fail_reason = res
        success, res = SMSService.send_twilio(message, phone)
        if success:
            SMSService._log_sms(phone, template, message, 'twilio', 'DELIVERED')
            return True, "Sent via Twilio Fallback"
        
        # Both failed
        SMSService._log_sms(phone, template, message, 'fast2sms', 'FAILED', error=f"F2S: {fail_reason} | Twilio: {res}")
        return False, f"All providers failed. Last error: {res}"

    @staticmethod
    def send_fast2sms(message, numbers):
        api_key = SMSService._get_config('f2s_key') or current_app.config.get('FAST2SMS_API_KEY')
        
        if not api_key or api_key == 'YOUR_FAST2_SMS_KEY':
            return False, "API Key not configured"
            
        url = "https://www.fast2sms.com/dev/bulkV2"
        payload = {"message": message, "language": "english", "route": "p", "numbers": numbers}
        headers = {'authorization': api_key, 'Content-Type': "application/x-www-form-urlencoded"}
        
        try:
            response = requests.post(url, data=payload, headers=headers)
            res_json = response.json()
            if res_json.get('return'):
                return True, "Success"
            return False, res_json.get('message', 'Failed')
        except Exception as e:
            return False, str(e)

    @staticmethod
    def send_twilio(message, to_number):
        sid = SMSService._get_config('twilio_sid')
        token = SMSService._get_config('twilio_token')
        from_phone = SMSService._get_config('twilio_phone')

        if not sid or not token or not from_phone:
            return False, "Twilio not configured"

        try:
            # Twilio uses Basic Auth
            url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
            response = requests.post(url, data={'To': to_number, 'From': from_phone, 'Body': message}, auth=(sid, token))
            if response.status_code in [200, 201]:
                return True, "Success"
            return False, response.text
        except Exception as e:
            return False, str(e)

    @staticmethod
    def notify_exit(student_name, parent_phone, student_phone, destination, expected_return):
        message = f"UniShield ALERT: Student {student_name} has left campus for {destination}. Expected return: {expected_return}."
        return SMSService.send_sms(parent_phone, message, 'EXIT')

    @staticmethod
    def notify_return(student_name, parent_phone, student_phone):
        message = f"UniShield ALERT: Student {student_name} has returned to campus safely."
        return SMSService.send_sms(parent_phone, message, 'RETURN')

    @staticmethod
    def notify_overdue(student_name, parent_phone, student_phone, expected_return):
        message = f"UniShield CRITICAL: Student {student_name} is OVERDUE! Expected return was {expected_return}."
        return SMSService.send_sms(parent_phone, message, 'OVERDUE')

    @staticmethod
    def notify_blacklisted(student_name, parent_phone, student_phone):
        message = f"UniShield ALERT: Student {student_name} has been BLACKLISTED. Access blocked."
        return SMSService.send_sms(parent_phone, message, 'BLACKLIST')
