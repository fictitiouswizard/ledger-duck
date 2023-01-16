import os
import smtplib

smtp_username = os.environ["smtp_username"]
smtp_password = os.environ["smtp_password"]
smtp_server = os.environ["smtp_server"]
smtp_port = int(os.environ["smtp_port"])


def send_password_reset_email(token: str, email_address: str):

    sender = "Duck Ledger <mail@duckledger.com>"
    receiver = email_address

    message = f"""\
Subject: Password Reset
To: {receiver}
From: {sender}


Someone has requested resetting your password.  If this was you please visit the following link to reset your password.

https://www.duckledger.com/password_reset/{token}
    """

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.login(smtp_username, smtp_password)
        server.sendmail(sender, receiver, message)