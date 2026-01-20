"""
Email service for sending OTPs and notifications.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL or "dark7stars@gmail.com"
        self.from_name = settings.SMTP_FROM_NAME or "Hospital Management System"

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body (optional)

        Returns:
            True if email was sent successfully
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            # Add plain text version
            if body_text:
                part1 = MIMEText(body_text, "plain")
                msg.attach(part1)

            # Add HTML version
            part2 = MIMEText(body_html, "html")
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to_email, msg.as_string())

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    async def send_otp(self, to_email: str, otp: str) -> bool:
        """
        Send OTP verification email.

        Args:
            to_email: Recipient email address
            otp: The OTP code

        Returns:
            True if email was sent successfully
        """
        subject = "Your Verification Code - Hospital Management System"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2563eb; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                .otp-box {{ background-color: #fff; border: 2px dashed #2563eb; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px; }}
                .otp-code {{ font-size: 32px; font-weight: bold; color: #2563eb; letter-spacing: 8px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
                .warning {{ color: #dc2626; font-size: 14px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Email Verification</h1>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>Thank you for registering with Hospital Management System. Please use the following OTP to verify your email address:</p>

                    <div class="otp-box">
                        <div class="otp-code">{otp}</div>
                    </div>

                    <p>This code will expire in <strong>10 minutes</strong>.</p>

                    <p class="warning">⚠️ If you didn't request this code, please ignore this email.</p>

                    <p>Best regards,<br>Hospital Management System Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = f"""
        Email Verification - Hospital Management System

        Hello,

        Thank you for registering with Hospital Management System.
        Please use the following OTP to verify your email address:

        Your OTP: {otp}

        This code will expire in 10 minutes.

        If you didn't request this code, please ignore this email.

        Best regards,
        Hospital Management System Team
        """

        return await self.send_email(to_email, subject, body_html, body_text)

    async def send_welcome_email(self, to_email: str, name: str) -> bool:
        """
        Send welcome email after successful registration.

        Args:
            to_email: Recipient email address
            name: User's name

        Returns:
            True if email was sent successfully
        """
        subject = "Welcome to Hospital Management System"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2563eb; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome!</h1>
                </div>
                <div class="content">
                    <p>Hello {name},</p>
                    <p>Welcome to Hospital Management System! Your account has been successfully created.</p>
                    <p>You can now:</p>
                    <ul>
                        <li>Book appointments with doctors</li>
                        <li>View your medical records</li>
                        <li>Access prescriptions and lab results</li>
                        <li>Manage your profile</li>
                    </ul>
                    <p>If you have any questions, please contact our support team.</p>
                    <p>Best regards,<br>Hospital Management System Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = f"""
        Welcome to Hospital Management System!

        Hello {name},

        Welcome to Hospital Management System! Your account has been successfully created.

        You can now:
        - Book appointments with doctors
        - View your medical records
        - Access prescriptions and lab results
        - Manage your profile

        If you have any questions, please contact our support team.

        Best regards,
        Hospital Management System Team
        """

        return await self.send_email(to_email, subject, body_html, body_text)


# Create singleton instance
email_service = EmailService()
