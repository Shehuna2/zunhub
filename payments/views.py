from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db import transaction
from django.utils.crypto import get_random_string
from .forms import DepositForm
from .models import CurrencyRate, DepositRequest
from p2p.models import Wallet
from .utils import initiate_flutterwave_payment
import hmac
import hashlib
import json
import logging
logger = logging.getLogger(__name__)



@login_required
def deposit(request):
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            currency = form.cleaned_data['currency']
            amount = form.cleaned_data['amount']
            try:
                rate = CurrencyRate.objects.get(currency=currency)
                ngn_amount = amount * rate.effective_rate()
            except CurrencyRate.DoesNotExist:
                return render(request, 'payments/deposit.html', {'form': form, 'error': 'Currency not supported'})

            tx_ref = get_random_string(12)
            deposit_request = DepositRequest.objects.create(
                user=request.user,
                currency=currency,
                amount=amount,
                ngn_amount=ngn_amount,
                tx_ref=tx_ref
            )

            redirect_url = request.build_absolute_uri('/payments/deposit/callback/')
            payment_link = initiate_flutterwave_payment(
                tx_ref=tx_ref,
                amount=amount,
                currency=currency,
                redirect_url=redirect_url,
                customer_email=request.user.email,
                customer_name=request.user.get_full_name() or request.user.username,
            )
            if payment_link:
                return redirect(payment_link)
            else:
                return render(request, 'payments/deposit.html', {'form': form, 'error': 'Failed to initiate payment'})
    else:
        form = DepositForm()
    return render(request, 'payments/deposit.html', {'form': form})

def deposit_callback(request):
    tx_ref = request.GET.get('tx_ref', '')
    if tx_ref:
        return render(request, 'payments/deposit_callback.html', {'message': 'Payment processing, please wait.'})
    return render(request, 'payments/deposit_callback.html', {'message': 'Invalid callback.'})

@csrf_exempt
def flutterwave_webhook(request):
    if request.method == 'POST':
        from django.conf import settings
        secret_key = settings.FLUTTERWAVE_HASH_KEY
        
        verif_hash = request.headers.get('HTTP_X_FLWR_SIGNATURE') or request.headers.get('X-FLWR-SIGNATURE')

        if not verif_hash:
            logger.warning('Missing Flutterwave signature header')
            return JsonResponse({'status': 'no verif-hash'}, status=400)

        if verif_hash:
            computed_hash = hmac.new(secret_key.encode(), request.body, hashlib.sha256).hexdigest()
            if computed_hash == verif_hash:
                data = json.loads(request.body)
                event = data.get('event')
                if event == 'charge.completed':
                    tx_ref = data.get('txRef')
                    try:
                        with transaction.atomic():
                            deposit_request = DepositRequest.objects.select_for_update().get(
                                tx_ref=tx_ref, status='pending'
                            )
                            deposit_request.status = 'successful'
                            deposit_request.save()
                            wallet, _ = Wallet.objects.select_for_update().get_or_create(user=deposit_request.user)
                            wallet.balance += deposit_request.ngn_amount
                            wallet.save()
                    except DepositRequest.DoesNotExist:
                        pass  # Log this in production
                return JsonResponse({'status': 'success'})
            return JsonResponse({'status': 'invalid hash'}, status=400)
        return JsonResponse({'status': 'no verif-hash'}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)