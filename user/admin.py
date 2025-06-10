from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db.models import JSONField 
from django.utils.html import format_html
from .models import (
    Profile, BlockedIP, BannedAccount, LoginHistory, UserActivityLog,
    ReferralBonus, UserLevelReward, UserSettings, Notification,
    AccountRestriction
)

# ================== INLINE ADMIN CLASSES ==================
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fieldsets = (
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'phone', 'email', 'avatar', 'preferred_payment')
        }),
        ('Financial', {
            'fields': ('balance', 'active_investment', 'referral_earnings', 'has_invested', 'investment_count')
        }),
        ('Verification', {
            'fields': ('is_verified', 'kyc_status', 'kyc_submitted_at', 'kyc_reviewed_at')
        }),
        ('Security', {
            'fields': ('is_banned', 'login_attempts', 'is_flagged', 'flagged_reason')
        }),
        ('Referral', {
            'fields': ('referral_code', 'referred_by')
        }),
        ('Metadata', {
            'fields': ('signup_ip', 'last_login_ip', 'last_seen', 'is_online')
        }),
    )

# ================== CUSTOM USER ADMIN ==================
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_kyc_status', 'get_balance', 'is_banned')
    list_select_related = ('profile',)
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__kyc_status', 'profile__is_banned')
    search_fields = ('username', 'email', 'profile__first_name', 'profile__last_name', 'profile__phone')

    def get_kyc_status(self, instance):
        return instance.profile.kyc_status
    get_kyc_status.short_description = 'KYC Status'
    get_kyc_status.admin_order_field = 'profile__kyc_status'

    def get_balance(self, instance):
        return f"₱{instance.profile.balance:,.2f}"
    get_balance.short_description = 'Balance'
    get_balance.admin_order_field = 'profile__balance'

    def is_banned(self, instance):
        return instance.profile.is_banned
    is_banned.boolean = True
    is_banned.short_description = 'Banned'
    is_banned.admin_order_field = 'profile__is_banned'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)

# ================== MODEL ADMIN CLASSES ==================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'phone', 'balance', 'kyc_status', 'is_banned', 'account_type')
    list_filter = ('kyc_status', 'is_banned', 'account_type', 'is_verified', 'city', 'region')
    search_fields = ('user__username', 'first_name', 'last_name', 'phone', 'email')
    readonly_fields = ('referral_code', 'created_at', 'updated_at')
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'first_name', 'last_name', 'phone', 'email', 'avatar', 'gcash_number', 'maya_number')
        }),
        ('Financial', {
            'fields': ('balance', 'active_investment', 'referral_earnings', 'has_invested', 'investment_count')
        }),
        ('Verification', {
            'fields': ('is_verified', 'kyc_status', 'kyc_submitted_at', 'kyc_reviewed_at', 'kyc_reviewer', 'phone_confirmed', 'email_confirmed')
        }),
        ('Security', {
            'fields': ('is_banned', 'login_attempts', 'is_flagged', 'flagged_reason')
        }),
        ('Referral', {
            'fields': ('referral_code', 'referred_by')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'signup_ip', 'last_login_ip', 'last_seen', 'is_online')
        }),
    )
    actions = ['approve_kyc', 'reject_kyc', 'ban_users']

    def approve_kyc(self, request, queryset):
        queryset.update(
            kyc_status='approved',
            kyc_reviewed_at=timezone.now(),
            kyc_reviewer=request.user,
            is_verified=True
        )
    approve_kyc.short_description = "Approve selected KYC submissions"

    def reject_kyc(self, request, queryset):
        queryset.update(
            kyc_status='rejected',
            kyc_reviewed_at=timezone.now(),
            kyc_reviewer=request.user,
            is_verified=False
        )
    reject_kyc.short_description = "Reject selected KYC submissions"

    def ban_users(self, request, queryset):
        for profile in queryset:
            BannedAccount.objects.get_or_create(
                user=profile.user,
                defaults={
                    'reason_choice': 'other',
                    'custom_reason': 'Banned via admin action',
                    'banned_by': request.user
                }
            )
        queryset.update(is_banned=True)
    ban_users.short_description = "Ban selected users"

@admin.register(BlockedIP)
class BlockedIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'blocked_until', 'is_active', 'created_by', 'reason')
    list_filter = ('blocked_until',)
    search_fields = ('ip_address', 'reason')
    actions = ['extend_block']

    def extend_block(self, request, queryset):
        for ip in queryset:
            ip.blocked_until = timezone.now() + timedelta(days=7)
            ip.save()
    extend_block.short_description = "Extend block by 7 days"

@admin.register(BannedAccount)
class BannedAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'reason_display', 'banned_by', 'created_at')
    list_filter = ('reason_choice', 'created_at')
    search_fields = ('user__username', 'custom_reason')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'created_at', 'was_successful', 'is_suspicious')
    list_filter = ('was_successful', 'is_suspicious', 'created_at')
    search_fields = ('user__username', 'ip_address', 'device')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(ReferralBonus)
class ReferralBonusAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'referred_user', 'bonus_amount', 'is_paid', 'created_at')
    list_filter = ('is_paid', 'created_at')
    search_fields = ('referrer__username', 'referred_user__username')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(UserLevelReward)
class UserLevelRewardAdmin(admin.ModelAdmin):
    list_display = ('level', 'required_exp', 'reward_bonus', 'badge_name')
    list_editable = ('required_exp', 'reward_bonus')
    ordering = ('level',)

@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'dark_mode', 'email_notifications', 'two_factor_auth')
    search_fields = ('user__username',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['mark_as_read']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected notifications as read"

@admin.register(AccountRestriction)
class AccountRestrictionAdmin(admin.ModelAdmin):
    list_display = ('user', 'restriction_type', 'is_active', 'expires_at', 'created_by')
    list_filter = ('restriction_type', 'is_active', 'expires_at')
    search_fields = ('user__username', 'reason')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['deactivate_restrictions']

    def deactivate_restrictions(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_restrictions.short_description = "Deactivate selected restrictions"

# ================== REGISTER/UNREGISTER ==================
admin.site.unregister(User)
admin.site.register(User, UserAdmin)