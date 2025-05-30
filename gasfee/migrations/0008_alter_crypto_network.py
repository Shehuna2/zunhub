# Generated by Django 5.1.7 on 2025-03-29 10:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gasfee', '0007_crypto_network_alter_crypto_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='crypto',
            name='network',
            field=models.CharField(choices=[('ETH', 'Ethereum'), ('BNB', 'Binance Smart Chain'), ('ARB', 'Arbitrum'), ('BASE', 'Base'), ('OP', 'Optimism')], max_length=50),
        ),
    ]
