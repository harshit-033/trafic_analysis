import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# --- Twilio Config ---
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")
ALERT_PHONE = os.getenv("ALERT_PHONE_NUMBER")

if TWILIO_SID and TWILIO_AUTH:
    client_sms = Client(TWILIO_SID, TWILIO_AUTH)
else:
    client_sms = None

def send_alert_sms(message: str):
    """Send SMS alert using Twilio"""
    try:
        if client_sms:
            client_sms.messages.create(
                body=message,
                from_=TWILIO_PHONE,
                to=ALERT_PHONE
            )
            print("[SMS SENT]", message)
        else:
            print("[SMS FAILED] Twilio credentials missing")
    except Exception as e:
        print("[SMS FAILED]", e)
