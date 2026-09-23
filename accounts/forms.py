import re
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class CitizenSignupForm(forms.Form):
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-3d',
            'placeholder': 'e.g. Rajesh',
            'autocomplete': 'given-name',
        }),
        label="First Name"
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-3d',
            'placeholder': 'e.g. Sharma',
            'autocomplete': 'family-name',
        }),
        label="Last Name"
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-3d',
            'placeholder': 'e.g. rajesh_sharma',
            'autocomplete': 'username',
        }),
        label="Username",
        help_text="Letters, numbers and @/./+/-/_ only"
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-3d',
            'placeholder': 'name@example.com',
            'autocomplete': 'email',
        }),
        label="Email Address",
        help_text="Verification OTP will be sent to this email address"
    )
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-3d',
            'placeholder': '+91 9876543210',
            'autocomplete': 'tel',
        }),
        label="Phone Number (Optional)"
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-3d',
            'placeholder': '••••••••',
            'autocomplete': 'new-password',
            'id': 'signup-password',
        }),
        label="Password",
        help_text="At least 6 characters with a combination of letters and numbers"
    )
    confirm_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-3d',
            'placeholder': '••••••••',
            'autocomplete': 'new-password',
            'id': 'signup-confirm-password',
        }),
        label="Confirm Password"
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not re.match(r'^[\w.@+-]+$', username):
            raise ValidationError("Enter a valid username with letters, digits, and @/./+/-/_ only.")
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already registered. Please choose another.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists. Please sign in instead.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                self.add_error('confirm_password', "Passwords do not match.")
            elif len(password) < 6:
                self.add_error('password', "Password must be at least 6 characters long.")
        return cleaned_data


class OTPVerifyForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-3d otp-main-input text-center fw-bold fs-3 letter-spacing-lg',
            'placeholder': '• • • • • •',
            'maxlength': '6',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
            'autofocus': 'autofocus',
        }),
        label="Enter 6-Digit OTP Code"
    )

    def clean_otp_code(self):
        code = self.cleaned_data.get('otp_code', '').strip()
        if not code.isdigit() or len(code) != 6:
            raise ValidationError("Please enter a valid 6-digit numeric OTP code.")
        return code
