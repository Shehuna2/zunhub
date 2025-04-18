# Generated by Django 5.1.7 on 2025-04-04 18:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gasfee', '0010_alter_crypto_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='crypto',
            name='network',
            field=models.CharField(choices=[('ETH', 'Ethereum'), ('BNB', 'Binance Smart Chain'), ('ARB', 'Arbitrum'), ('BASE', 'Base'), ('OP', 'Optimism'), ('SOL', 'Solana'), ('TON', 'Toncoin'), ('SUI', 'Sui'), ('NEAR', 'Near')], max_length=50),
        ),
    ]
