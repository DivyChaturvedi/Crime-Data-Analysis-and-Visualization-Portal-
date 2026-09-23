import random
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings


class EmailOTP(models.Model):
    """
    Stores 6-digit Email One-Time-Password (OTP) for verifying citizen registration
    and securing citizen authentication actions. Includes brute-force protection
    and rate-limiting controls.
    """
    MAX_FAILED_ATTEMPTS = 5

    email = models.EmailField(db_index=True)
    otp_code = models.CharField(max_length=6)
    signup_payload = models.JSONField(default=dict, help_text="Serialized user registration data")
    is_verified = models.BooleanField(default=False)
    failed_attempts = models.PositiveIntegerField(default=0, help_text="Count of consecutive incorrect attempts")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Email OTP Verification"
        verbose_name_plural = "Email OTP Verifications"

    def __str__(self):
        status = "Verified" if self.is_verified else ("Expired" if self.is_expired() else ("Locked" if self.is_locked() else "Pending"))
        return f"OTP for {self.email} [{status}] ({self.otp_code})"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_locked(self):
        return self.failed_attempts >= self.MAX_FAILED_ATTEMPTS

    def is_valid(self, input_code):
        if self.is_verified:
            return False, "This OTP has already been verified."
        if self.is_expired():
            return False, "OTP has expired. Please request a new code."
        if self.is_locked():
            return False, "Too many incorrect attempts. This OTP is locked for security. Please request a fresh code."

        clean_input = str(input_code).strip()
        clean_target = str(self.otp_code).strip()

        if clean_target != clean_input:
            self.failed_attempts += 1
            self.save(update_fields=['failed_attempts'])
            remaining = self.MAX_FAILED_ATTEMPTS - self.failed_attempts
            if remaining <= 0:
                return False, "Security Alert: Maximum attempts exceeded. This OTP has been invalidated."
            return False, f"Incorrect verification code. {remaining} attempt(s) remaining."

        # Reset failed attempts on success
        if self.failed_attempts > 0:
            self.failed_attempts = 0
            self.save(update_fields=['failed_attempts'])

        return True, "Valid OTP"

    @classmethod
    def create_for_signup(cls, email, payload, expiry_minutes=10):
        # Invalidate any prior active OTPs for this email
        cls.objects.filter(email=email, is_verified=False).delete()

        # Generate a cryptographically strong 6-digit numeric OTP code
        otp = f"{random.SystemRandom().randint(100000, 999999)}"
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)

        instance = cls.objects.create(
            email=email,
            otp_code=otp,
            signup_payload=payload,
            expires_at=expires_at,
            failed_attempts=0,
        )
        return instance

    def send_verification_email(self):
        """Dispatches official branded verification email to the user."""
        subject = f"🔐 Your CDAVP Portal Verification Code: {self.otp_code}"
        
        plain_message = (
            f"Dear Citizen,\n\n"
            f"Thank you for registering on the CDAVP Crime Intelligence & Public Safety Portal.\n\n"
            f"Your 6-Digit Email Verification Code is:\n"
            f"----------------------------------------\n"
            f"           {self.otp_code}\n"
            f"----------------------------------------\n\n"
            f"This code will expire in 10 minutes. For security reasons, do NOT share this code with anyone.\n\n"
            f"If you did not initiate this registration, please ignore this email.\n\n"
            f"Regards,\n"
            f"CDAVP Command & Public Safety Center\n"
            f"Government of Madhya Pradesh"
        )

        html_message = f"""
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 16px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px rgba(0,0,0,0.06);">
            <div style="background: linear-gradient(135deg, #0a1128 0%, #1e3a8a 100%); padding: 32px 24px; text-align: center; color: #ffffff;">
                <div style="font-size: 32px; margin-bottom: 8px;">🛡️</div>
                <h1 style="margin: 0; font-size: 22px; font-weight: 800; letter-spacing: 0.5px;">CDAVP PORTAL</h1>
                <p style="margin: 6px 0 0 0; font-size: 13px; color: #93c5fd; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600;">Crime Intelligence & Citizen Safety</p>
            </div>
            
            <div style="padding: 32px 28px; color: #1e293b;">
                <h2 style="font-size: 18px; font-weight: 700; margin-top: 0; color: #0f172a;">Citizen Account Verification</h2>
                <p style="font-size: 14px; line-height: 1.6; color: #475569;">
                    Thank you for signing up. Please enter the following 6-digit One-Time Password (OTP) to complete your verification and activate your account.
                </p>
                
                <div style="margin: 28px 0; padding: 20px; background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 12px; text-align: center;">
                    <span style="font-size: 36px; font-weight: 800; letter-spacing: 10px; color: #2563eb; font-family: monospace;">{self.otp_code}</span>
                    <p style="margin: 8px 0 0 0; font-size: 12px; color: #64748b; font-weight: 500;">Valid for 10 minutes only</p>
                </div>

                <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; border-radius: 6px; margin-bottom: 24px;">
                    <p style="margin: 0; font-size: 12.5px; color: #1e40af; line-height: 1.5;">
                        <strong>Security Notice:</strong> Never share your verification code or credentials with anyone. CDAVP officers will never ask for your OTP.
                    </p>
                </div>

                <p style="font-size: 13px; color: #64748b; margin-bottom: 0;">
                    If you did not create an account on CDAVP, you can safely disregard this message.
                </p>
            </div>

            <div style="background: #f1f5f9; padding: 16px 24px; text-align: center; border-top: 1px solid #e2e8f0; font-size: 11.5px; color: #94a3b8;">
                CDAVP Command Center • Emergency Helpline: 100 / 1090 • Khargone District
            </div>
        </div>
        """

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@cdavp.gov.in'),
                recipient_list=[self.email],
                html_message=html_message,
                fail_silently=False,
            )
            return True
        except Exception as e:
            if settings.DEBUG:
                print(f"[CDAVP EMAIL OTP] Email dispatch to {self.email} failed or used console backend: {e}")
                print(f"[CDAVP EMAIL OTP] OTP CODE: {self.otp_code}")
            return False
