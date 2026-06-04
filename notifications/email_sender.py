import logging
import smtplib

from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class EmailSender:

    def __init__(
        self,
        smtp_email,
        smtp_password,
        smtp_server="smtp.gmail.com",
        smtp_port=587,
    ):

        self.smtp_email = smtp_email

        self.smtp_password = smtp_password

        self.smtp_server = smtp_server

        self.smtp_port = smtp_port

    # =====================================================
    # SEND CONFIRMATION EMAIL
    # =====================================================

    def send_booking_confirmation(
        self,
        booking_state,
    ):

        if (
            not self.smtp_email
            or not self.smtp_password
        ):

            logger.warning(
                "Email credentials missing."
            )

            return

        subject = (
            "Appointment Confirmation"
        )

        body = f"""
Hello {booking_state.name},

Your appointment has been confirmed.

Service:
{booking_state.service_type}

Date:
{booking_state.date}

Time:
{booking_state.time}

Contact:
{booking_state.contact}

Booking ID:
{booking_state.event_id}

Thank you.
"""

        msg = MIMEText(body)

        msg["Subject"] = subject

        msg["From"] = self.smtp_email

        msg["To"] = booking_state.email

        try:

            with smtplib.SMTP(
                self.smtp_server,
                self.smtp_port,
            ) as server:

                server.set_debuglevel(1)
                server.starttls()
                server.login(self.smtp_email, self.smtp_password)

                logger.info(
                    f"SMTP Email: {self.smtp_email}"
                )

                logger.info(
                    f"Password Length: {len(self.smtp_password) if self.smtp_password else 0}"
                )

                server.send_message(msg)

            logger.info(
                "Confirmation email sent."
            )

        except Exception as e:

            logger.exception(
                f"Email sending failed: {e}"
            )