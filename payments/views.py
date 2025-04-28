from django.shortcuts import render, redirect, reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
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

def healthcheck_ping(request):
    return JsonResponse({"status": "ok"})

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

            redirect_url = settings.BASE_URL + reverse('deposit_callback')
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
    if request.method != "POST":
        return JsonResponse({"status": "invalid method"}, status=405)

    # Use HASH KEY, not SECRET KEY
    expected_hash = getattr(settings, "FLUTTERWAVE_HASH_KEY", "").strip()
    logger.info("🔑 Using expected hash: %r", expected_hash)

    received_hash = (
        request.META.get("HTTP_VERIF_HASH")
        or request.headers.get("verif-hash")
        or ""
    ).strip().strip("\"'")

    logger.info("📥 Received header hash: %r", received_hash)

    if not received_hash or received_hash != expected_hash:
        logger.warning(
            "Invalid webhook signature: expected=%s, received=%s",
            expected_hash,
            received_hash
        )
        return JsonResponse({"status": "invalid hash"}, status=400)

    logger.info("✅ Webhook signature matched")

    try:
        payload = json.loads(request.body)
        event = payload.get("event")
        data = payload.get("data", {})

        if event == "charge.completed" and data.get("status") == "successful":
            tx_ref = data.get("tx_ref") or data.get("txRef")
            with transaction.atomic():
                dr = DepositRequest.objects.select_for_update().get(
                    tx_ref=tx_ref,
                    status="pending"
                )
                dr.status = "successful"
                dr.save()

                wallet, _ = Wallet.objects.select_for_update().get_or_create(user=dr.user)
                wallet.balance += dr.ngn_amount
                wallet.save()

                logger.info("💰 Deposit processed for tx_ref: %s", tx_ref)

    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        return JsonResponse({"status": "invalid payload"}, status=400)
    except DepositRequest.DoesNotExist:
        logger.warning("No pending DepositRequest for tx_ref: %s", tx_ref)
        return JsonResponse({"status": "no deposit request"}, status=400)
    except Exception as e:
        logger.exception("Error processing webhook: %s", e)
        return JsonResponse({"status": "processing error"}, status=500)

    return JsonResponse({"status": "success"})
