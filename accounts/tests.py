import json
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from accounts.models import EmailOTP


class EmailOTPTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.payload = {
            'username': 'newcitizen',
            'email': 'newcitizen@example.com',
            'password': 'Password@123',
            'first_name': 'New',
            'last_name': 'Citizen',
            'phone_number': '+91 9988776655'
        }

    def test_create_and_validate_otp(self):
        otp_obj = EmailOTP.create_for_signup(
            email='test@example.com',
            payload=self.payload,
            expiry_minutes=10
        )
        self.assertEqual(len(otp_obj.otp_code), 6)
        self.assertTrue(otp_obj.otp_code.isdigit())
        self.assertFalse(otp_obj.is_expired())

        # Validate with correct code
        is_valid, msg = otp_obj.is_valid(otp_obj.otp_code)
        self.assertTrue(is_valid)

    def test_otp_brute_force_lockout(self):
        otp_obj = EmailOTP.create_for_signup(
            email='lockout@example.com',
            payload=self.payload,
            expiry_minutes=10
        )
        # Attempt 5 wrong inputs
        for i in range(5):
            is_valid, msg = otp_obj.is_valid("000000")
            self.assertFalse(is_valid)

        self.assertTrue(otp_obj.is_locked())
        # Even correct code should now fail because locked
        is_valid_locked, msg_locked = otp_obj.is_valid(otp_obj.otp_code)
        self.assertFalse(is_valid_locked)
        self.assertIn("locked", msg_locked.lower())

    def test_expired_otp(self):
        otp_obj = EmailOTP.create_for_signup(
            email='expire@example.com',
            payload=self.payload,
            expiry_minutes=-5  # expired 5 min ago
        )
        self.assertTrue(otp_obj.is_expired())
        is_valid, msg = otp_obj.is_valid(otp_obj.otp_code)
        self.assertFalse(is_valid)
        self.assertIn("expired", msg.lower())

    def test_signup_to_verify_flow(self):
        # 1. Post to register
        signup_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'username': 'testcitizen2026',
            'email': 'testcitizen2026@cdavp.gov.in',
            'phone_number': '9876543210',
            'password': 'SecurePassword@123',
            'confirm_password': 'SecurePassword@123',
        }
        resp = self.client.post(reverse('register'), data=signup_data)
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('verify_otp'))

        # Check OTP record created
        otp_obj = EmailOTP.objects.get(email='testcitizen2026@cdavp.gov.in')
        self.assertFalse(otp_obj.is_verified)

        # 2. Get verify-otp page
        get_resp = self.client.get(reverse('verify_otp'))
        self.assertEqual(get_resp.status_code, 200)

        # 3. Post correct OTP
        verify_resp = self.client.post(reverse('verify_otp'), {'otp_code': otp_obj.otp_code})
        self.assertEqual(verify_resp.status_code, 302)
        self.assertRedirects(verify_resp, reverse('dashboard'))

        # Verify user created and authenticated
        user_exists = User.objects.filter(username='testcitizen2026').exists()
        self.assertTrue(user_exists)
        user = User.objects.get(username='testcitizen2026')
        self.assertEqual(user.email, 'testcitizen2026@cdavp.gov.in')

        # Check raw password was wiped from payload
        otp_obj.refresh_from_db()
        self.assertNotIn('password', otp_obj.signup_payload)

    def test_resend_otp_rate_limiting(self):
        # Set session
        otp_obj = EmailOTP.create_for_signup(email='resend@example.com', payload=self.payload)
        session = self.client.session
        session['pending_otp_email'] = 'resend@example.com'
        session['pending_otp_id'] = otp_obj.id
        session.save()

        # Immediate resend should be rate limited (429 status)
        resp = self.client.post(reverse('resend_otp'))
        self.assertEqual(resp.status_code, 429)
        data = resp.json()
        self.assertFalse(data.get('success'))
        self.assertIn('Rate limit', data.get('message'))
