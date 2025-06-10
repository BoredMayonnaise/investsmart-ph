from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'user'

urlpatterns = [
    path('banned/', views.banned_notice, name='banned_notice'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

]
