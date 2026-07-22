import json
from core.email_sender import send_email

def test_email():
    with open('data/jobs.json', 'r') as f:
        settings = json.load(f)
        
    hr_email = settings.get("hr_email")
    hr_password = settings.get("hr_password")
    
    print("Attempting to send a test email...")
    print(f"From/To: {hr_email}")
    
    # We will send a test email from the HR email to the HR email
    subject = "Test Email from Resume Analyzer"
    body = "This is a test email to verify that the SMTP settings are working correctly."
    
    result = send_email(hr_email, subject, body, hr_email, hr_password)
    print("Send Email Result:", result)

if __name__ == "__main__":
    test_email()
