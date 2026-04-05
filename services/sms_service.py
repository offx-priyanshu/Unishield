import os
import requests

class SMSService:
    @staticmethod
    def send_sms(to_number, message):
        """
        Send SMS using Fast2SMS or Twilio.
        Mock implementation for now.
        """
        print(f"Sending SMS to {to_number}: {message}")
        
        # Fast2SMS example (uncomment if credentials available)
        # url = "https://www.fast2sms.com/dev/bulkV2"
        # payload = {
        #     "message": message,
        #     "language": "english",
        #     "route": "q",
        #     "numbers": to_number,
        # }
        # headers = {
        #     "authorization": os.environ.get("FAST2SMS_API_KEY"),
        #     "Content-Type": "application/x-www-form-urlencoded",
        #     "Cache-Control": "no-cache",
        # }
        # response = requests.request("POST", url, data=payload, headers=headers)
        # return response.json()
        
        return {"status": "success", "message": "SMS sent successfully (Mocked)"}

    @staticmethod
    def notify_parent(parent_phone, student_name, action):
        message = f"Alert: SNOX Outpass. {student_name} has {action} from the campus. Please check portal for details."
        return SMSService.send_sms(parent_phone, message)

    @staticmethod
    def alert_overdue(parent_phone, student_name, limit_time):
        message = f"Urgent: {student_name} is overdue for return since {limit_time}. Please contact immediately."
        return SMSService.send_sms(parent_phone, message)
