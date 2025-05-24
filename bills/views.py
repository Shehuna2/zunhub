import re
from django.http import JsonResponse
from django.contrib import messages
from django.template.loader import render_to_string
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.contrib.admin.views.decorators import staff_member_required

from django.db import transaction
from decimal import Decimal
from p2p.models import Wallet, Order, Dispute
from .utils import purchase_airtime, purchase_data, get_data_plans
import logging
from django.utils import timezone

from io import BytesIO
from datetime import datetime, timedelta

from .forms import SellStep1Form, PaymentProofForm
from .models import AssetSellOrder, ExchangeInfo
from .services import lookup_rate, get_receiving_details

logger = logging.getLogger(__name__)


@login_required
def sell_step1(request):
    if request.method == 'POST':
        form = SellStep1Form(request.POST)
        if form.is_valid():
            asset  = form.cleaned_data['asset']
            source = form.cleaned_data['source']
            amt    = form.cleaned_data['amount_asset']

            # ❗ Prevent duplicate order with same parameters and pending/awaiting status
            duplicate = AssetSellOrder.objects.filter(
                user=request.user,
                asset=asset,
                source=source,
                amount_asset=amt,
                status__in=['pending', 'awaiting_confirmation']
            ).exists()

            if duplicate:
                form.add_error(None, "You already have a similar pending order. Please complete it first.")
                return render(request, 'bills/asset_sell_step1.html', {'form': form})

            try:
                # Attempt to fetch the rate
                rate = lookup_rate(asset, source)
            except Exception:
                form.add_error(None, "Unable to fetch live exchange rate right now. Please try again in a moment.")
                return render(request, 'bills/asset_sell_step1.html', {'form': form})

            total_ngn = (amt * rate).quantize(Decimal('0.01'))

            order = AssetSellOrder.objects.create(
                user=request.user,
                asset=asset,
                source=source,
                amount_asset=amt,
                rate_ngn=rate,
                amount_ngn=total_ngn,
            )
            return redirect('sell_step2', order_id=order.id)
    else:
        form = SellStep1Form()

    return render(request, 'bills/asset_sell_step1.html', {'form': form})


@login_required
def sell_step2(request, order_id):
    order = get_object_or_404(AssetSellOrder, pk=order_id, user=request.user)

    # Populate receiving details if empty
    if not order.details:
        order.details = get_receiving_details(order.source, order.asset)
        order.save()

    logger.info("SELL_STEP2 – order.details: %r", order.details)

    expired = timezone.now() > (order.created_at + timedelta(minutes=10))
    proof_form = None

    if request.method == 'POST':
        if order.source != "binance" and not expired:
            proof_form = PaymentProofForm(request.POST, request.FILES)
            if proof_form.is_valid():
                proof = proof_form.save(commit=False)
                proof.order = order
                proof.save()
            else:
                print("[❌ FORM ERRORS]", proof_form.errors)


        # Now update order status
        order.status = 'awaiting_confirmation'
        order.save()
        return redirect('sell_done', order_id=order.id)
    else:
        if order.source != "binance" and not expired:
            proof_form = PaymentProofForm()

    # Prepare QR content as plain UID or email
    uid = order.details.get('uid')
    email = order.details.get('email')
    qr_data = uid or email or ''

    # Fetch exchange info
    try:
        exch = ExchangeInfo.objects.get(exchange=order.source)
        qr_url = exch.receive_qr.url
        contact = exch.contact_info
    except ExchangeInfo.DoesNotExist:
        qr_url = None
        contact = order.details

    return render(request, "bills/asset_sell_step2.html", {
        "order":      order,
        "details":    order.details,
        "qr_url":     qr_url,
        "expires_at": (order.created_at + timedelta(minutes=10)).isoformat(),
        "proof_form": proof_form,
        "expired":    expired,
    })

@login_required
def order_status(request, order_id):
    order = get_object_or_404(AssetSellOrder, pk=order_id, user=request.user)
    return JsonResponse({"status": order.status})

@login_required
def sell_done(request, order_id):
    order = get_object_or_404(AssetSellOrder, pk=order_id, user=request.user)
    return render(request, 'bills/asset_sell_done.html', {'order': order})


def admin_dashboard_refresh(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    context = {
        'to_credit_orders': AssetSellOrder.objects.filter(status='awaiting_confirmation').order_by('-created_at')[:5],
        'recent_disputes': Dispute.objects.all().order_by('-created_at')[:10],
        'total_orders': AssetSellOrder.objects.count(),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'completed_orders': AssetSellOrder.objects.filter(status='completed').count(),
        'pending_disputes': Dispute.objects.exclude(status='resolved').count(),
        'awaiting_confirmation': AssetSellOrder.objects.filter(status='awaiting_confirmation').count(),
    }

    html_credit_orders = render_to_string('partials/_awaiting_credit.html', context, request)
    html_disputes = render_to_string('partials/_recent_disputes.html', context, request)
    html_summary = render_to_string('partials/_summary_cards.html', context, request)

    return JsonResponse({
        'credit_orders': html_credit_orders,
        'recent_disputes': html_disputes,
        'summary_cards': html_summary,
    })


@staff_member_required
def awaiting_confirmation_list(request):
    orders = AssetSellOrder.objects.filter(status='awaiting_confirmation').order_by('-created_at')

    return render(request, 'bills/awaiting_list.html', {'page_obj': orders})

@user_passes_test(lambda u: u.is_superuser)
def admin_credit_order(request, order_id):
    order = get_object_or_404(AssetSellOrder, pk=order_id, status="awaiting_confirmation")

    if request.method == "POST":
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=order.user)
            wallet.balance += order.amount_ngn
            wallet.save()
            order.status = "completed"
            order.save()

        # Detect AJAX and return JSON rather than redirect
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "order_id": order.id,
                "awaiting_confirmation": AssetSellOrder.objects.filter(status="awaiting_confirmation").count(),
                "completed_orders": AssetSellOrder.objects.filter(status="completed").count(),
            })

    # Fallback for non-AJAX (e.g. direct POST from browser)
    messages.success(request, f"Order #{order.id} credited successfully.")
    return redirect("admin_dashboard")


@login_required
def sell_order_history(request):
    orders = AssetSellOrder.objects.filter(user=request.user)

    # Filtering
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')

    if search_query:
        orders = orders.filter(id__icontains=search_query)
    
    if status_filter:
        orders = orders.filter(status=status_filter)

    orders = orders.order_by('-created_at')

    return render(request, 'bills/asset_sell_history.html', {
        'orders': orders,
        'search_query': search_query,
        'status_filter': status_filter,
    })


PHONE_REGEX = re.compile(r'^0[7-9][0-1]\d{8}$')

def calculator(request):
    return render(request, "bills/calculator.html")

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
                        'transaction_id': result['transaction_id'],
                        'transaction_date': result.get('transaction_date'),
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
    
