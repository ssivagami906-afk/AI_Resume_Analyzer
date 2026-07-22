import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os

def send_email(to_email: str, subject: str, body: str, from_email: str, password: str, attachment_data: bytes = None, attachment_name: str = None):
    """Sends an email using SMTP, optionally with an attachment."""
    if not from_email or not password:
        print("Error: Email credentials not provided.")
        return False
        
    # Remove any spaces that might have been accidentally copied with the App Password
    password = password.replace(" ", "").strip()
    from_email = from_email.strip()
        
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        if attachment_data and attachment_name:
            part = MIMEApplication(attachment_data, Name=attachment_name)
            part['Content-Disposition'] = f'attachment; filename="{attachment_name}"'
            msg.attach(part)
        
        # Use Gmail's SMTP server by default
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        return True
    except smtplib.SMTPAuthenticationError:
        print("SMTP Authentication Error: Invalid App Password.")
        return False
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_approval_email(candidate_email: str, hr_email: str, hr_password: str, reason: str):
    subject = "Update on your Job Application - Approved for Interview"
    body = f"Congratulations!\n\nYour resume has been shortlisted for an interview.\n\nFeedback: {reason}\n\nOur HR team will contact you soon."
    return send_email(candidate_email, subject, body, hr_email, hr_password)

def send_decline_email(candidate_email: str, hr_email: str, hr_password: str, reason: str):
    subject = "Update on your Job Application"
    body = f"Thank you for applying.\n\nUnfortunately, we will not be moving forward with your application at this time.\n\nFeedback: {reason}\n\nWe wish you the best in your job search."
    return send_email(candidate_email, subject, body, hr_email, hr_password)
    
def notify_hr(hr_email: str, hr_password: str, candidate_email: str, candidate_name: str, reason: str, is_approved: bool, resume_bytes: bytes = None):
    status = "APPROVED" if is_approved else "REJECTED"
    subject = f"New Candidate {status}: {candidate_name} ({candidate_email})"
    body = f"A new candidate has been analyzed by the AI.\n\nCandidate Name: {candidate_name}\nCandidate Email: {candidate_email}\nAI Decision: {status}\nAI Summary: {reason}\n\nPlease find the candidate's resume attached."
    
    attachment_name = f"{candidate_name.replace(' ', '_')}_Resume.pdf" if resume_bytes else None
    return send_email(hr_email, subject, body, hr_email, hr_password, attachment_data=resume_bytes, attachment_name=attachment_name)
