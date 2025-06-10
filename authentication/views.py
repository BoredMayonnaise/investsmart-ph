
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from ip_finder.ip import get_client_ip, get_location_from_ip, get_geo_data
from user.models import Profile, BlockedIP, LoginHistory, ReferralBonus
from django.db.models import F, Value, IntegerField, DecimalField
from django.utils.timezone import now
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
import re
import datetime
import requests
from django.http import HttpResponseNotAllowed
from django.db import transaction
from decimal import Decimal
import logging
logger = logging.getLogger(__name__)

def login_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip()
        password   = request.POST.get('password', '').strip()
        ip         = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        device_fp  = request.POST.get('device_fingerprint', '')
        geo        = get_geo_data(ip) or {}

        location_parts = [geo.get('city'), geo.get('region'), geo.get('country')]
        location = ', '.join([p for p in location_parts if p]) or 'Unknown'

        if not identifier or not password:
            messages.error(request, "Please enter both username/email and password.")
            return render(request, 'auth/login.html')

        username = identifier
        if '@gmail.com' in identifier:
            try:
                user_obj = User.objects.get(email__iexact=identifier)
                username = user_obj.username
            except User.DoesNotExist:
                username = None

        user = authenticate(request, username=username, password=password) if username else None

        # --- LOG THE ATTEMPT (always) -----------------
        LoginHistory.objects.create(
            user=user,                       # may be None now
            attempted_identifier=identifier, # what was typed
            ip_address=ip,
            device=device_fp,
            user_agent=user_agent,
            location=location,
            was_successful=bool(user),
            failure_reason="" if user else "Invalid credentials",
            is_suspicious=not bool(user),
        )
        # ----------------------------------------------

        if user:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('authentication:redirect_view')
        else:
            messages.error(request, "Invalid username/email or password.")
            return render(request, 'auth/login.html')

    return render(request, 'auth/login.html')
    
@transaction.atomic
def register_view(request):
    if request.method == 'POST':
        referral_code = request.POST.get('referral_code') or request.session.pop('referral_code', None)
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        device_fp = request.POST.get('device_fingerprint', '')

        twenty_five_days_ago = now() - datetime.timedelta(days=25)
        year_ago = now() - datetime.timedelta(days=365)
        ip = get_client_ip(request)
        geo = get_geo_data(ip) or {}

        errors = []
        # Password checks
        if not password or not confirm_password:
            errors.append("Password fields cannot be empty.")
        elif password != confirm_password:
            errors.append("Passwords do not match.")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        elif not any(char.isdigit() for char in password):
            errors.append("Password must contain at least one number.")
        elif not any(char.isupper() for char in password):
            errors.append("Password must contain at least one uppercase letter.")
        elif not any(char.islower() for char in password):
            errors.append("Password must contain at least one lowercase letter.")

        # Username checks
        if not username:
            errors.append("Username cannot be empty.")
        elif len(username) < 4:
            errors.append("Username must be at least 4 characters long.")
        elif not username.isalnum():
            errors.append("Username can only contain letters and numbers.")

        # Email checks
        if not email:
            errors.append("Email cannot be empty.")
        elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            errors.append("Please enter a valid email address.")

        # Uniqueness checks
        if User.objects.filter(username__iexact=username).exists():
            errors.append("Username already exists.")
        if User.objects.filter(email__iexact=email).exists():
            errors.append("Email already in use.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('authentication:register')

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            # Create profile with all required fields
            profile_data = {
                'user': user,
                'email': email,
                'signup_ip': ip,
                'city': geo.get('city', ''),
                'region': geo.get('region', ''),
                'country': geo.get('country', ''),
                'org': geo.get('org', ''),
                'first_name': '',
                'last_name': '',
                'phone': None,
            }
            
            profile = Profile.objects.create(**profile_data)

            # Handle referral logic
            if referral_code:
                try:
                    referrer_profile = Profile.objects.select_for_update().get(
                        referral_code=referral_code.upper(),
                        user__is_active=True
                    )
                    profile.referred_by = referrer_profile.user
                    profile.save()  # Save the reference

                    # Update referrer's counts
                    Profile.objects.filter(user=referrer_profile.user).update(
                        referral_count=F('referral_count') + 1,
                        points=F('points') + 1
                    )

                    ReferralBonus.objects.get_or_create(
                        referrer=referrer_profile.user,
                        referred_user=user,
                        defaults={
                            'bonus_amount': Decimal('0.00'),
                            'is_paid': False,
                            'referral_source': request.session.pop('referral_source', 'direct')
                        }
                    )

                except Profile.DoesNotExist:
                    logger.warning(f"Invalid referral code used: {referral_code}")
                except Exception as e:
                    logger.error(f"Referral processing failed: {str(e)}")

            # Log registration history
            location_parts = [geo.get('city'), geo.get('region'), geo.get('country')]
            location = ', '.join(filter(None, location_parts))

            LoginHistory.objects.create(
                user=user,
                ip_address=ip,
                device=device_fp,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                location=location,
                was_successful=True,
                is_registration=True
            )

            messages.success(request, "Registration successful! Please log in.")
            return redirect('authentication:login')

        except Exception as e:
            logger.error(f"User registration failed: {str(e)}", exc_info=True)
            messages.error(request, "Registration failed due to a server error. Please try again.")
            return redirect('authentication:register')

    return render(request, 'auth/register.html')

def logout(request):
    if request.method == 'POST':
        auth_logout(request)
        messages.info(request, "You have been logged out.")
        return redirect('authentication:redirect_view')
    else:
        return HttpResponseNotAllowed(['POST'])

@require_GET
def check_username(request):
    username = request.GET.get('username', '').strip()
    if not username:
        return JsonResponse({'available': False, 'error': 'No username provided'})

    is_taken = User.objects.filter(username__iexact=username).exists()
    return JsonResponse({'available': not is_taken})

EMAIL_REGEX = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

@require_GET
def check_email(request):
    email = request.GET.get('email', '').strip()

    if not email:
        return JsonResponse({'valid': False, 'error': 'No email provided'})

    if not re.match(EMAIL_REGEX, email):
        return JsonResponse({'valid': False, 'error': 'Invalid email format'})

    is_taken = User.objects.filter(email__iexact=email).exists()
    return JsonResponse({'valid': not is_taken, 'taken': is_taken})

def check_phone(request):
    phone = request.GET.get('phone')
    is_taken = Profile.objects.filter(phone=phone).exists()
    return JsonResponse({'available': not is_taken})
    
def redirect_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            target_url = 'admin:index'
        else:
            profile = getattr(request.user, 'profile', None)
            if profile and profile.kyc_status != 'approved':
                target_url = 'authentication:submit'
            else:
                target_url = 'user:dashboard'
    else:
        target_url = 'authentication:login'

    return render(request, 'redirect/redirect.html', {
        'target_url': target_url
    })

@login_required
def verify_account(request):
    profile = request.user.profile

    if profile.email_confirmed and profile.phone_confirmed and profile.kyc_status == 'approved':
        messages.success(request, "Your account is fully verified.")
        return redirect('user:dashboard')

    if profile.kyc_status == 'pending':
        messages.info(request, "Your KYC is under review. Please wait for verification.")
    elif profile.kyc_status == 'approved':
        messages.success(request, "Your KYC is already approved.")
        return redirect('user:dashboard')
    elif profile.kyc_status in ['not_submitted', 'rejected', None, 'unverified']:
        return redirect('authentication:submit')

    return render(request, 'verify/information.html', {
        'profile': profile,
        'kyc_pending': profile.kyc_status == 'pending',
        'email_confirmed': profile.email_confirmed,
        'phone_confirmed': profile.phone_confirmed,
    })

@login_required
def submit_kyc(request):
    profile = request.user.profile

    # Allow resubmission if rejected
    if profile.kyc_status == 'approved':
        messages.success(request, "Your KYC is already approved.")
        return redirect('authentication:verify_account')

    if profile.kyc_status == 'pending':
        messages.info(request, "Your KYC is under review.")
        return redirect('authentication:verify_account')

    if request.method == 'POST':
        avatar = request.FILES.get('avatar')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        preferred_payment = request.POST.get('preferred_payment')
        gcash_number = request.POST.get('gcash_number')
        maya_number = request.POST.get('maya_number')

        # Basic validation
        if not all([first_name, last_name, phone, preferred_payment]):
            messages.error(request, "Please fill out all required fields.")
        else:
            profile.avatar = avatar
            profile.first_name = first_name
            profile.last_name = last_name
            profile.phone = phone
            profile.preferred_payment = preferred_payment
            profile.gcash_number = gcash_number
            profile.maya_number = maya_number
            profile.kyc_status = 'pending'
            profile.kyc_submitted_at = timezone.now()
            profile.save()

            messages.success(request, "KYC submitted successfully. Await approval.")
            return redirect('authentication:verify_account')

    return render(request, 'verify/submit.html')

# @login_required
# def resend_email_verification(request):
#     profile = request.user.profile

#     if profile.email_confirmed:
#         messages.info(request, "Your email is already verified.")
#         return redirect('first')

#     # TODO: Integrate actual email sending logic
#     messages.success(request, "Verification email has been resent.")
#     return redirect('first')


# @login_required
# def resend_sms_verification(request):
#     profile = request.user.profile

#     if profile.phone_confirmed:
#         messages.info(request, "Your phone number is already verified.")
#         return redirect('first')

#     # TODO: Integrate actual SMS sending logic
#     messages.success(request, "Verification SMS has been resent.")
#     return redirect('first')


@login_required
def kyc_upload(request):
    profile = request.user.profile

    if request.method == 'POST':
        # Example placeholder logic — you’d replace this with actual form/file handling
        profile.kyc_status = 'pending'
        profile.save()
        messages.success(request, "KYC documents submitted successfully. Please wait for approval.")
        return redirect('first')

    return render(request, 'auth/kyc_upload.html')
