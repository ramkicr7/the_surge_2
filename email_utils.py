import smtplib
from email.mime.text import MIMEText
import random
import threading

MAIL_EMAIL = "ramkishoreelumalai@gmail.com"
MAIL_PASSWORD = "kzzg pszg jgvm jlqq"


def send_email_async(to_email, subject, body):

    def send():
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = MAIL_EMAIL
            msg["To"] = to_email

            server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server.login(MAIL_EMAIL, MAIL_PASSWORD)
            server.sendmail(MAIL_EMAIL, to_email, msg.as_string())
            server.quit()

        except Exception as e:
            print("EMAIL ERROR:", e)

    thread = threading.Thread(target=send)
    thread.start()


def generate_tpin():
    return str(random.randint(1000, 9999))


def generate_otp():
    return str(random.randint(100000, 999999))