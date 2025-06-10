import uuid
import json
from django.db import models
from django.db.models import JSONField 
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from user_agents import parse

# Constants (moved to top for better organization)
ACCOUNT_TYPES = (
    ('free', 'Free'),
    ('investor', 'Investor'),
    ('admin', 'Admin'),
)

KYC_STATUS = (
    ('unverified', 'Unverified'),
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
)

PAYMENT_METHODS = (
    ('gcash', 'GCash'),
    ('maya', 'Maya'),
    ('both', 'GCash & Maya'),
)

BAN_REASONS = (
    ('multiple_accounts', 'Multiple Accounts'),
    ('fraud', 'Fraudulent Activity'),
    ('abuse', 'Platform Abuse'),
    ('kyc_violation', 'KYC Violation'),
    ('spamming', 'Spamming/Advertising'),
    ('other', 'Other (custom reason below)'),
)

# ================== MIXINS & ABSTRACT MODELS ==================
class GeoLocationMixin(models.Model):
    """Shared location fields for multiple models"""
    city = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    org = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        abstract = True

class TimestampMixin(models.Model):
    """Adds created_at and updated_at fields"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# ================== MAIN MODELS ==================
class Profile(GeoLocationMixin, TimestampMixin, models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    email = models.EmailField(blank=True, null=True, db_index=True)

    # Name and contact
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20, db_index=True, unique=True, blank=True, null=True)

    # Referral system
    referral_code = models.CharField(max_length=10, unique=True, blank=True, db_index=True)
    referred_by = models.ForeignKey(User, related_name='referrals', null=True, blank=True, on_delete=models.SET_NULL)
    referral_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    referral_count = models.PositiveIntegerField(default=0, null=True, blank=True)

    # Financials
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    active_investment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    investment_goal = models.DecimalField(max_digits=12, decimal_places=2, default=100000.00,help_text="Target investment goal set by the user")
    has_invested = models.BooleanField(default=False)
    points = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    investment_count = models.PositiveIntegerField(default=0)
    last_deposit_date = models.DateTimeField(blank=True, null=True)
    last_withdrawal_date = models.DateTimeField(blank=True, null=True)

    # Payment Info
    preferred_payment = models.CharField(blank=True, null=True, max_length=10, choices=PAYMENT_METHODS, default='gcash')
    gcash_number = models.CharField(max_length=20, blank=True, null=True, default='None')
    maya_number = models.CharField(max_length=20, blank=True, null=True,  default='None')

    # Verification
    is_verified = models.BooleanField(default=False, db_index=True)
    email_confirmed = models.BooleanField(default=False)
    phone_confirmed = models.BooleanField(default=False)
    kyc_status = models.CharField(max_length=10, choices=KYC_STATUS, default='unverified', db_index=True)
    kyc_submitted_at = models.DateTimeField(blank=True, null=True)
    kyc_reviewed_at = models.DateTimeField(blank=True, null=True)
    kyc_reviewer = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='kyc_reviews')

    # Security
    is_banned = models.BooleanField(default=False, db_index=True)
    login_attempts = models.PositiveIntegerField(default=0)
    flagged_reason = models.TextField(blank=True, null=True)
    is_flagged = models.BooleanField(default=False)

    # Gamification
    level = models.PositiveIntegerField(default=1)
    experience = models.PositiveIntegerField(default=0)
    next_level_exp = models.PositiveIntegerField(default=100)

    # Admin
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES, default='free', db_index=True)
    notes = models.TextField(blank=True)

    # Metadata
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    signup_ip = models.GenericIPAddressField(blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    is_online = models.BooleanField(default=False)
    last_password_change = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['is_verified', 'kyc_status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} ({self.full_name})"


    def clean(self):

        # Disallow negative balances
        if self.balance < 0:
            raise ValidationError("Balance cannot be negative.")

        if self.uses_gcash and not self.gcash_number:
            raise ValidationError({"gcash_number": "GCash number is required when GCash is the preferred payment."})
        if self.uses_maya and not self.maya_number:
            raise ValidationError({"maya_number": "Maya number is required when Maya is the preferred payment."})

        if self.phone:
            existing = Profile.objects.filter(phone=self.phone).exclude(user=self.user)
            if existing.exists():
                raise ValidationError({"phone": "This phone number is already used by another account."})

        # Clean KYC fields if user is resubmitting after rejection
        if self.kyc_status == 'rejected':
            self.kyc_status = 'unverified'
            self.phone = None
            self.gcash_number = None
            self.maya_number = None
            self.preferred_payment = None
            self.kyc_reviewer = None
            self.kyc_reviewed_at = None
            self.kyc_submitted_at = timezone.now()

    def save(self, *args, **kwargs):
        self.full_clean()

    def generate_referral_code(self):
        """Generate unique referral code"""
        while True:
            code = uuid.uuid4().hex[:8].upper()
            if not Profile.objects.filter(referral_code=code).exists():
                return code

            if not profile.referral_code:
                profile.referral_code = profile.generate_referral_code()

    def level_up(self):
        """Handle level progression"""
        self.level += 1
        self.experience -= self.next_level_exp
        self.next_level_exp = int(self.next_level_exp * 1.5)

        # Handle level-up logic
        while self.experience >= self.next_level_exp:
            self.level_up()

        super().save(*args, **kwargs)

    @property
    def investment_progress_percent(self):
        if self.investment_goal > 0:
            return min(round((self.active_investment / self.investment_goal) * 100, 2), 100)
        return 0

    @property
    def uses_gcash(self):
        return self.preferred_payment == 'gcash'

    @property
    def uses_maya(self):
        return self.preferred_payment == 'maya'

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def total_referrals(self):
        return self.user.referrals.count()

    def get_absolute_url(self):
        return reverse('profile_detail', kwargs={'pk': self.user.pk})

    def get_payment_methods(self):
        methods = []
        if self.uses_gcash():
            methods.append(f"GCash ({self.gcash_number})")
        if self.uses_maya():
            methods.append(f"Maya ({self.maya_number})")
        return " & ".join(methods) if methods else "No payment method set"

    @classmethod
    def ban_user(cls, user, reason=""):
        """Ban a user and create audit record"""
        BannedAccount.objects.get_or_create(
            user=user,
            defaults={'reason_choice': 'other', 'custom_reason': reason}
        )
        cls.objects.filter(user=user).update(is_banned=True)

# ================== SECURITY MODELS ==================
class BlockedIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    blocked_until = models.DateTimeField()
    reason = models.TextField(blank=True)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.ip_address} (until {self.blocked_until})"

    def is_active(self):
        return self.blocked_until > timezone.now()

    def save(self, *args, **kwargs):
        if not self.blocked_until:
            self.blocked_until = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

class BannedAccount(TimestampMixin, models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='banned_account')
    reason_choice = models.CharField(max_length=30, choices=BAN_REASONS, default='other')
    custom_reason = models.TextField(blank=True, null=True)
    banned_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='banned_users')

    def __str__(self):
        return f"{self.user.username} banned for {self.reason_display}"

    @property
    def reason_display(self):
        return self.custom_reason if self.reason_choice == 'other' else self.get_reason_choice_display()

# ================== USER ACTIVITY MODELS ==================
class LoginHistory(TimestampMixin, models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,   # keep row even if the user is deleted
        null=True,                   # ← allow NULL in DB
        blank=True,
        related_name='login_history'
    )
    attempted_identifier = models.CharField(
        max_length=254, blank=True
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    device = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=100, blank=True)
    was_successful = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=100, blank=True)
    is_suspicious = models.BooleanField(default=False)
    is_registration = models.BooleanField(default=False)

    def __str__(self):
        user_part = self.user.username if self.user else self.attempted_identifier or "unknown user"
        status = "success" if self.was_successful else "failed"
        return f"{user_part} login {status} from {self.ip_address}"

    def get_device_info(self):
        user_agent = parse(self.user_agent)
        return {
            "browser": f"{user_agent.browser.family} {user_agent.browser.version_string}",
            "os": f"{user_agent.os.family} {user_agent.os.version_string}",
            "device": user_agent.device.family or "Unknown Device"
        }

class UserActivityLog(TimestampMixin, models.Model):
    ACTION_CHOICES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('profile_update', 'Profile Update'),
        ('password_change', 'Password Change'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField()
    metadata = JSONField(default=dict)  # Store additional context

    def __str__(self):
        return f"{self.user.username} {self.get_action_display()} at {self.created_at}"

# ================== REFERRAL & REWARDS ==================
class ReferralBonus(TimestampMixin, models.Model):
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referral_bonuses')
    referred_user = models.OneToOneField(User, on_delete=models.CASCADE)
    bonus_amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('referrer', 'referred_user')
        verbose_name_plural = 'Referral Bonuses'

    def clean(self):
        if self.referrer == self.referred_user:
            raise ValidationError("User cannot refer themselves")

    def __str__(self):
        return f"₱{self.bonus_amount} for {self.referrer.username}"

class UserLevelReward(models.Model):
    level = models.PositiveIntegerField(unique=True)
    required_exp = models.PositiveIntegerField()
    reward_bonus = models.DecimalField(max_digits=5, decimal_places=2)
    badge_name = models.CharField(max_length=50)
    icon = models.ImageField(upload_to='level_badges/', blank=True)

    class Meta:
        ordering = ['level']

    def clean(self):
        if self.level > 1:
            prev_level = UserLevelReward.objects.filter(level=self.level-1).first()
            if prev_level and self.required_exp <= prev_level.required_exp:
                raise ValidationError("Required EXP must increase with each level")

    def __str__(self):
        return f"Level {self.level}: {self.badge_name}"

# ================== NOTIFICATION & SETTINGS ==================
class UserSettings(TimestampMixin, models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    dark_mode = models.BooleanField(default=False)
    language = models.CharField(max_length=10, default='en')
    email_notifications = models.BooleanField(default=True)
    two_factor_auth = models.BooleanField(default=False)

    def __str__(self):
        return f"Settings for {self.user.username}"

class Notification(TimestampMixin, models.Model):
    NOTIFICATION_TYPES = (
        ('system', 'System'),
        ('investment', 'Investment'),
        ('withdrawal', 'Withdrawal'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=100)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    metadata = models.JSONField()

    class Meta:
        ordering = ['-created_at']

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save()

    @classmethod
    def unread_count(cls, user):
        return cls.objects.filter(user=user, is_read=False).count()

    def __str__(self):
        return f"{self.title} for {self.user.username}"

# ================== ACCOUNT RESTRICTIONS ==================
class AccountRestriction(TimestampMixin, models.Model):
    RESTRICTION_TYPES = (
        ('withdrawal', 'Withdrawals Blocked'),
        ('investment', 'New Investments Blocked'),
        ('login', 'Login Temporarily Disabled'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='restrictions')
    restriction_type = models.CharField(max_length=20, choices=RESTRICTION_TYPES)
    reason = models.TextField()
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='imposed_restrictions')

    def clean(self):
        if self.restriction_type == 'login' and not self.expires_at:
            raise ValidationError("Login restrictions require an expiration time")

    def save(self, *args, **kwargs):
        if self.expires_at and self.expires_at < timezone.now():
            self.is_active = False
        super().save(*args, **kwargs)

    @classmethod
    def cleanup_expired(cls):
        cls.objects.filter(expires_at__lt=timezone.now(), is_active=True).update(is_active=False)

    def __str__(self):
        return f"{self.user.username}: {self.get_restriction_type_display()}"

