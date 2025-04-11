from django.http import JsonResponse
from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.db import transaction
from decimal import Decimal
from p2p.models import Wallet
from .utils import purchase_airtime, purchase_data, get_data_plans
import logging
import re

logger = logging.getLogger(__name__)

PHONE_REGEX = re.compile(r'^0[7-9][0-1]\d{8}$')

@login_required
def buy_airtime(request):
    if request.method == "POST":
        phone = request.POST.get("phone")
        try:
            amount = Decimal(request.POST.get("amount", "0"))
        except Decimal.InvalidOperation:
            amount = Decimal(0)
        network = request.POST.get("network", "").lower()
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if not phone or not PHONE_REGEX.match(phone) or amount <= 0 or network not in ["mtn", "glo", "airtel", "9mobile"]:
            error_message = "Invalid input. Phone must be a valid 11-digit Nigerian number."
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_message})
            messages.error(request, error_message)
            return redirect("buy-airtime")

        try:
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=request.user)
                if wallet.balance < amount:
                    error_message = f"Insufficient balance: ₦{wallet.balance}"
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': error_message})
                    messages.error(request, error_message)
                    return redirect("buy-airtime")

                wallet.balance -= amount
                wallet.save()

                result = purchase_airtime(phone, float(amount), network)
                success_message = (
                    f"₦{amount} airtime sent to {phone}! "
                    f"Transaction ID: {result['transaction_id']}"
                )
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': success_message,
                        'transaction_id': result['transaction_id']
                    })
                messages.success(request, success_message)

        except Wallet.DoesNotExist:
            error_message = "Wallet not found."
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_message})
            messages.error(request, error_message)
            return redirect("buy-airtime")
        except ValueError as e:
            error_message = str(e)
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_message})
            messages.error(request, error_message)
            return redirect("buy-airtime")
        except Exception as e:
            logger.error(f"Unexpected error in buy_airtime: {e}")
            error_message = "An unexpected error occurred."
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_message})
            messages.error(request, error_message)
            return redirect("buy-airtime")

        return redirect("buy-airtime")

    return render(request, "bills/buy_airtime.html")

@login_required
def buy_data(request):
    if request.method == "POST":
        phone = request.POST.get("phone")
        try:
            amount = Decimal(request.POST.get("amount", "0"))
        except Decimal.InvalidOperation:
            amount = Decimal(0)
        network = request.POST.get("network", "").lower()
        variation_code = request.POST.get("variation_code", "")
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if (
            not phone or not PHONE_REGEX.match(phone) or
            amount <= 0 or
            network not in ["mtn", "glo", "airtel", "9mobile"] or
            not variation_code
        ):
            error_message = "Invalid input. Phone must be a valid 11-digit Nigerian number."
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_message})
            messages.error(request, error_message)
            return redirect("buy-data")

        try:
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=request.user)
                if wallet.balance < amount:
                    error_message = f"Insufficient balance: ₦{wallet.balance}"
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': error_message})
                    messages.error(request, error_message)
                    return redirect("buy-data")

                wallet.balance -= amount
                wallet.save()

                result = purchase_data(phone, float(amount), network, variation_code)
                success_message = (
                    f"₦{amount} data bundle sent to {phone}! "
                    f"Transaction ID: {result['transaction_id']}"
                )
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': success_message,
                        'transaction_id': result['transaction_id']
                    })
                messages.success(request, success_message)

        except Wallet.DoesNotExist:
            error_message = "Wallet not found."
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_message})
            messages.error(request, error_message)
            return redirect("buy-data")
        except ValueError as e:
            error_message = str(e)
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_message})
            messages.error(request, error_message)
            return redirect("buy-data")
        except Exception as e:
            logger.error(f"Unexpected error in buy_data: {e}")
            error_message = "An unexpected error occurred."
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_message})
            messages.error(request, error_message)
            return redirect("buy-data")

        return redirect("buy-data")

    return render(request, "bills/buy_data.html")

@login_required
def get_data_plans_api(request):
    """API endpoint to fetch data plans for a given network."""
    network = request.GET.get("network", "").lower()
    if network not in ["mtn", "glo", "airtel", "9mobile"]:
        return JsonResponse({"success": False, "message": "Invalid network"}, status=400)

    try:
        plans = get_data_plans(network)
        return JsonResponse({"success": True, "plans": plans})
    except ValueError as e:
        return JsonResponse({"success": False, "message": str(e)}, status=503)
    except Exception as e:
        logger.error(f"Error fetching data plans: {e}")
        return JsonResponse({"success": False, "message": "An unexpected error occurred"}, status=500)