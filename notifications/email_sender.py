"""
Notifications — Email Sender.

Sends booking confirmation emails.
"""

import logging
import smtplib

from email.mime.multipart import (
    MIMEMultipart,
)

from email.mime.text import (
    MIMEText,
)

logger = logging.getLogger(__name__)


class EmailSender:

    # =====================================================
    # INIT
    # =====================================================

    def __init__(

        self,

        sender_email,

        sender_password,

        smtp_server="smtp.gmail.com",

        smtp_port=587,

    ):

        self.sender_email = sender_email

        self.sender_password = sender_password

        self.smtp_server = smtp_server

        self.smtp_port = smtp_port

        logger.info(

            f"EmailSender initialized "

            f"(server={smtp_server}:{smtp_port})."

        )

    # =====================================================
    # SEND BOOKING CONFIRMATION
    # =====================================================

    def send_booking_confirmation(

        self,

        booking_data,

    ):

        # =================================================
        # VALIDATE
        # =================================================

        if not booking_data.get("email"):

            raise ValueError(
                "Recipient email missing."
            )

        # =================================================
        # EMAIL CONTENT
        # =================================================

        subject = (
            "Appointment Confirmation"
        )

        body = f"""
Hello {booking_data.get('name')},

Your appointment has been confirmed.

==================================

Service:
{booking_data.get('service_type')}

Date:
{booking_data.get('date')}

Time:
{booking_data.get('time')}

Contact:
{booking_data.get('contact')}

Booking ID:
{booking_data.get('event_id')}

==================================

Thank you for choosing us.

Regards,
Aria AI Appointment System
"""

        # =================================================
        # MIME MESSAGE
        # =================================================

        message = MIMEMultipart()

        message["From"] = (
            self.sender_email
        )

        message["To"] = (
            booking_data.get("email")
        )

        message["Subject"] = subject

        message.attach(

            MIMEText(
                body,
                "plain",
            )

        )

        # =================================================
        # SMTP SEND
        # =================================================

        try:

            server = smtplib.SMTP(

                self.smtp_server,

                self.smtp_port,

                timeout=10,

            )

            server.starttls()

            server.login(

                self.sender_email,

                self.sender_password,

            )

            server.sendmail(

                self.sender_email,

                booking_data.get("email"),

                message.as_string(),

            )

            server.quit()

            logger.info(

                f"Confirmation email sent to "

                f"{booking_data.get('email')}"

            )

            return True

        except Exception as e:

            logger.error(
                f"Email sending failed: {e}"
            )

            return False

    # =====================================================
    # GENERIC SEND EMAIL
    # =====================================================

    def send_email(

        self,

        recipient_email,

        subject,

        body,

    ):

        try:

            message = MIMEMultipart()

            message["From"] = (
                self.sender_email
            )

            message["To"] = (
                recipient_email
            )

            message["Subject"] = subject

            message.attach(

                MIMEText(
                    body,
                    "plain",
                )

            )

            server = smtplib.SMTP(

                self.smtp_server,

                self.smtp_port,

                timeout=10,

            )

            server.starttls()

            server.login(

                self.sender_email,

                self.sender_password,

            )

            server.sendmail(

                self.sender_email,

                recipient_email,

                message.as_string(),

            )

            server.quit()

            logger.info(
                f"Email sent to "
                f"{recipient_email}"
            )

            return True

        except Exception as e:

            logger.error(
                f"Generic email failed: {e}"
            )

            return False