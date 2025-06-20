# Generated by Django 5.2.2 on 2025-06-08 12:21

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0006_accountrestriction_loginhistory_notification_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='loginhistory',
            options={},
        ),
        migrations.AddField(
            model_name='loginhistory',
            name='attempted_identifier',
            field=models.CharField(blank=True, max_length=254),
        ),
        migrations.AlterField(
            model_name='loginhistory',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='login_history', to=settings.AUTH_USER_MODEL),
        ),
    ]
