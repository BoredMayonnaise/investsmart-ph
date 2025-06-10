from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'authentication'

urlpatterns = [
    path('login/', views.login_view, name='login'),

    path('logout/', views.logout, name='logout'),

    path('register/', views.register_view, name='register'),

    path('check-username/', views.check_username, name='check_username'),

    path('check-email/', views.check_email, name='check_email'),

    path('check-phone/', views.check_phone, name='check_phone'),

    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('redirect/', views.redirect_view, name='redirect_view'),

    path('verify-account/', views.verify_account, name='verify_account'),
    path("submit/", views.submit_kyc, name="submit"),

    # path('resend-email-verification/', views.resend_email_verification, name='resend_email_verification'),
    # path('resend-sms-verification/', views.resend_sms_verification, name='resend_sms_verification'),
    # path('kyc-upload/', views.kyc_upload, name='kyc_upload'),
]
