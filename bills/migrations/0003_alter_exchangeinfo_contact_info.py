# Generated by Django 5.1.7 on 2025-05-17 13:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bills', '0002_exchangeinfo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exchangeinfo',
            name='contact_info',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
    ]
