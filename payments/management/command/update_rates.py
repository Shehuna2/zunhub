from django.core.management.base import BaseCommand
from payments.models import CurrencyRate

class Command(BaseCommand):
    help = 'Update currency rates'

    def handle(self, *args, **options):
        # Example rates (replace with real API call)
        rates = {'USD': 1650.00, 'EUR': 480.00, 'GBP': 550.00}  # Base rates to NGN
        for currency, base_rate in rates.items():
            rate, created = CurrencyRate.objects.get_or_create(currency=currency)
            rate.base_rate = base_rate
            rate.save()
        self.stdout.write(self.style.SUCCESS('Successfully updated currency rates'))