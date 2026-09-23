from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from crimes.models import CrimeRecord
from .models import EmailOTP
from .forms import CitizenSignupForm, OTPVerifyForm


def style_auth_form(form):
    for field in form.fields.values():
        field.widget.attrs.setdefault('class', 'form-control')
    return form


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = style_auth_form(AuthenticationForm(data=request.POST))
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            next_url = request.GET.get('next')
            return redirect(next_url if next_url else 'dashboard')
        messages.error(request, 'Invalid username or password. Please verify your credentials.')
    else:
        form = style_auth_form(AuthenticationForm())

    return render(request, 'accounts/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CitizenSignupForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            email = cd['email'].lower()

            payload = {
                'username': cd['username'],
                'email': email,
                'first_name': cd['first_name'],
                'last_name': cd['last_name'],
                'password': cd['password'],
                'phone_number': cd.get('phone_number', ''),
            }

            # Create Email OTP record and send email
            otp_obj = EmailOTP.create_for_signup(email=email, payload=payload, expiry_minutes=10)
            otp_obj.send_verification_email()

            # Save in session for verification view
            request.session['pending_otp_email'] = email
            request.session['pending_otp_id'] = otp_obj.id

            messages.info(request, f"Verification code sent to {email}. Please enter the 6-digit OTP to activate your account.")
            return redirect('verify_otp')
        else:
            messages.error(request, 'Please correct the highlighted registration errors.')
    else:
        form = CitizenSignupForm()

    return render(request, 'accounts/register.html', {'form': form})


def verify_otp_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    pending_email = request.session.get('pending_otp_email')
    pending_otp_id = request.session.get('pending_otp_id')

    if not pending_email or not pending_otp_id:
        messages.warning(request, "No pending registration found. Please fill the signup form.")
        return redirect('register')

    try:
        otp_obj = EmailOTP.objects.get(id=pending_otp_id, email=pending_email)
    except EmailOTP.DoesNotExist:
        messages.error(request, "Verification session expired. Please sign up again.")
        return redirect('register')

    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            input_code = form.cleaned_data['otp_code']
            is_valid, error_msg = otp_obj.is_valid(input_code)

            if is_valid:
                # Mark verified
                otp_obj.is_verified = True

                payload = otp_obj.signup_payload
                username = payload.get('username')
                email = payload.get('email')
                password = payload.get('password')
                first_name = payload.get('first_name', '')
                last_name = payload.get('last_name', '')

                # Sanitize payload in database to erase plaintext password after successful account creation
                otp_obj.signup_payload = {
                    'username': username,
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'verified_at': timezone.now().isoformat()
                }
                otp_obj.save()

                # Double check user doesn't already exist
                if User.objects.filter(username=username).exists():
                    user = User.objects.get(username=username)
                else:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        is_staff=False,
                        is_superuser=False
                    )

                # Clear session verification states
                request.session.pop('pending_otp_email', None)
                request.session.pop('pending_otp_id', None)

                # Authenticate and login
                authenticated_user = authenticate(username=username, password=password)
                if authenticated_user:
                    login(request, authenticated_user)
                else:
                    login(request, user)

                messages.success(request, f"🎉 Email verified successfully! Welcome to CDAVP, {user.first_name or user.username}!")
                return redirect('dashboard')
            else:
                messages.error(request, error_msg)
    else:
        form = OTPVerifyForm()

    context = {
        'form': form,
        'email': pending_email,
        'otp_code_preview': otp_obj.otp_code if settings.DEBUG else None,
        'expires_at_iso': otp_obj.expires_at.isoformat(),
        'attempts_remaining': EmailOTP.MAX_FAILED_ATTEMPTS - otp_obj.failed_attempts,
    }
    return render(request, 'accounts/verify_otp.html', context)


def resend_otp_view(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    pending_email = request.session.get('pending_otp_email')
    pending_otp_id = request.session.get('pending_otp_id')

    if not pending_email or not pending_otp_id:
        return JsonResponse({'success': False, 'message': 'No active signup session found.'}, status=400)

    try:
        old_otp = EmailOTP.objects.get(id=pending_otp_id, email=pending_email)
        
        # Server-side Rate Limiting: enforce minimum 45s cooldown
        elapsed = (timezone.now() - old_otp.created_at).total_seconds()
        if elapsed < 45:
            remaining = int(45 - elapsed)
            return JsonResponse({
                'success': False,
                'message': f'Rate limit: Please wait {remaining} more seconds before requesting another code.'
            }, status=429)

        payload = old_otp.signup_payload
        
        # Create fresh OTP
        new_otp = EmailOTP.create_for_signup(email=pending_email, payload=payload, expiry_minutes=10)
        new_otp.send_verification_email()
        
        request.session['pending_otp_id'] = new_otp.id

        return JsonResponse({
            'success': True,
            'message': f'A fresh 6-digit OTP has been sent to {pending_email}.',
            'debug_otp': new_otp.otp_code if settings.DEBUG else None,
            'expires_at_iso': new_otp.expires_at.isoformat()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error resending OTP: {str(e)}'}, status=500)


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been securely logged out.')
    return redirect('login')


@login_required
def profile_view(request):
    user = request.user
    my_crimes = CrimeRecord.objects.filter(reported_by=user).order_by('-created_at')

    total_reported = my_crimes.count()
    verified_count = my_crimes.filter(status__in=['approved', 'investigating', 'resolved']).count()
    resolved_count = my_crimes.filter(status='resolved').count()
    pending_count = my_crimes.filter(status='pending').count()

    context = {
        'user': user,
        'my_crimes': my_crimes,
        'total_reported': total_reported,
        'verified_count': verified_count,
        'resolved_count': resolved_count,
        'pending_count': pending_count,
    }
    return render(request, 'accounts/profile.html', context)
