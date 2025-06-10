from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BannedAccount, Profile, UserSettings
from django.contrib.auth.models import User
from ip_finder.ip import get_device_info, get_client_ip
from django.db import transaction
from .models import ReferralBonus, Profile
# from .utils import send_referral_notification  
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        UserSettings.objects.create(user=instance)

@receiver(post_save, sender=BannedAccount)
def flag_profile_as_banned(sender, instance, created, **kwargs):
    if created:
        try:
            profile = instance.user.profile
            profile.is_banned = True
            profile.save()
        except Profile.DoesNotExist:
            pass

from django.contrib.auth.signals import user_logged_in

@receiver(user_logged_in)
def log_device_info(sender, request, user, **kwargs):
    if user.is_staff or user.is_superuser:
        return 

    device_info = get_device_info(request)
    ip = get_client_ip(request)

    user.profile.last_login_device = device_info
    user.profile.last_login_ip = ip
    user.profile.save()

@receiver(post_save, sender=ReferralBonus)
def handle_referral_bonus(sender, instance, created, **kwargs):
    """Handle referral bonus when a new referral is created."""
    if created and not instance.bonus_credited:
        with transaction.atomic():
            referrer_profile = Profile.objects.select_for_update().get(user=instance.referrer)
            referred_profile = Profile.objects.select_for_update().get(user=instance.referred_user)

            has_invested = Investment.objects.filter(user=instance.referred_user, status='active').exists()

            referrer_bonus = 20 if has_invested else 10
            referred_bonus = 5

            referrer_profile.points += referrer_bonus
            referrer_profile.referral_count += 1
            referrer_profile.save()

            referred_profile.points += referred_bonus
            referred_profile.save()

            instance.bonus_credited = True
            instance.save()

            send_referral_notification(instance.referrer, instance.referred_user)

# def send_referral_notification(referrer, referred_user):
#     """Send email notifications for successful referrals"""
#     # Email to referrer
#     send_mail(
#         'New Referral!',
#         f'Congratulations! {referred_user.username} signed up using your referral link.',
#         settings.DEFAULT_FROM_EMAIL,
#         [referrer.email],
#         fail_silently=True,
#     )
    
#     # Email to referred user
#     send_mail(
#         'Welcome!',
#         f'Thanks for signing up through {referrer.username}\'s referral!',
#         settings.DEFAULT_FROM_EMAIL,
#         [referred_user.email],
#         fail_silently=True,
#     )

