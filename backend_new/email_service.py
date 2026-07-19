import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def send_review_email(customer_name, customer_email, review_link):
    subject = "Please Share Your Review"

    body = f"""
Hello {customer_name},

Thank you for choosing our service.

We would love to hear your feedback.

Please click the link below to submit your review:

{review_link}

Thank you,
ReviewShield Team
"""

    message = MIMEMultipart()
    message["From"] = SMTP_USER
    message["To"] = customer_email
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(message)
        server.quit()

        print(f"Email sent successfully to {customer_email}")
        return True

    except Exception as e:
        print("Email Error:", e)
        return False