from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.exceptions import ValidationError

from django.core.paginator import Paginator
from django.db import transaction
from decimal import Decimal
from django.db.models import Sum
from itertools import chain
from django.db.models import Value, CharField
from django.db.models import Count, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib import messages
from .forms import DisputeForm, WithdrawOfferForm, DepositOfferForm, WithdrawOrderForm, DepositOrderForm
from .models import Wallet, Dispute, Deposit_P2P_Offer, DepositOrder, Withdraw_P2P_Offer, WithdrawOrder
from bills.models import AssetSellOrder, PaymentProof
from gasfee.models import CryptoPurchase

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

User = get_user_model()

def merchant_required(function):
    return user_passes_test(lambda u: hasattr(u, 'is_merchant') and u.is_merchant)(function)


@merchant_required
@login_required
def create_withdraw_offer(request):
    if request.method == "POST":
        form = WithdrawOfferForm(request.POST, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                sell_offer = form.save(commit=False)
                sell_offer.merchant = request.user
                sell_offer.save()
                messages.success(request, "Withdraw offer created successfully.")
                return redirect("marketplace")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = WithdrawOfferForm(user=request.user)
    return render(request, "p2p/create_withdraw_offer.html", {"form": form})


@merchant_required
@login_required
def create_deposit_offer(request):
    if request.method == 'POST':
        form = DepositOfferForm(request.POST, user=request.user)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.merchant = request.user
            with transaction.atomic():
                offer.save()
                messages.success(request, "Sell offer created!")
                return redirect('marketplace')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DepositOfferForm(user=request.user)
    return render(request, 'p2p/create_deposit_offer.html', {'form': form})


login_required
def create_deposit_order(request, offer_id):
    """
    Buyer requests an order from a merchant.
    Combines:
      • atomic/row-locking for concurrency safety
      • Django form validation & messages
      • GET: render form; POST: process transaction and redirect
    """
    # 1) Fetch the active sell-offer
    sell_offer = get_object_or_404(Deposit_P2P_Offer, id=offer_id, is_available=True)

    # Check for self-order
    if request.user == sell_offer.merchant:
        messages.error(request, "You cannot place an order against your own offer.")
        return redirect('marketplace')

    if request.method == 'POST':
        # Pass both sell_offer and user into the form for proper validation
        form = DepositOrderForm(request.POST, sell_offer=sell_offer, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 2) Lock the offer row
                    offer_locked = Deposit_P2P_Offer.objects.select_for_update().get(id=offer_id)

                    amount = form.cleaned_data['amount_requested']
                    # 3) Lock the merchant's wallet under the same transaction
                    merchant_wallet = Wallet.objects.select_for_update().get(user=offer_locked.merchant)
                    if not merchant_wallet.lock_funds(amount):
                        available = merchant_wallet.balance - merchant_wallet.locked_balance
                        raise ValidationError(
                            f"Cannot create order: merchant only has ₦{available} available."
                        )

                    # 4) Create and save the deposit order
                    order = form.save(commit=False)
                    order.buyer = request.user
                    order.sell_offer = offer_locked
                    order.save()

                    # 5) Update the offer's available amount and deactivate if empty
                    offer_locked.amount_available -= amount
                    if offer_locked.amount_available <= 0:
                        offer_locked.is_available = False
                    offer_locked.save()

                messages.success(request, f"Deposit order #{order.id} created! Merchant’s funds escrowed.")
                return redirect('order_details', order.id)

            except ValidationError as e:
                messages.error(request, e.message)
        else:
            messages.error(request, "Invalid order details. Please check and try again.")
    else:
        # GET: instantiate blank form with sell_offer & user for widget attrs
        form = DepositOrderForm(sell_offer=sell_offer, user=request.user)

    return render(request, 'p2p/create_deposit_order.html', {
        'form': form,
        'sell_offer': sell_offer,
    })
    

@login_required
def create_withdraw_order(request, offer_id):
    """
    Place a sell-order against a merchant’s buy-offer with full transactional safety,
    form validation, and user feedback.
    """
    # 1) Fetch the active offer
    offer = get_object_or_404(Withdraw_P2P_Offer, id=offer_id, is_active=True)

    # Check for self-order
    if request.user == offer.merchant:
        messages.error(request, "You cannot place an order against your own offer.")
        return redirect('marketplace')

    if request.method == 'POST':
        # Pass both buy_offer and user into the form for proper validation
        form = WithdrawOrderForm(request.POST, buy_offer=offer, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 2) Lock the offer row to prevent race conditions
                    offer_locked = Withdraw_P2P_Offer.objects.select_for_update().get(id=offer_id)

                    amount = form.cleaned_data['amount_requested']

                    # 3) Lock the seller's wallet under the same transaction
                    wallet = Wallet.objects.select_for_update().get(user=request.user)
                    if not wallet.lock_funds(amount):
                        raise ValidationError("You don't have enough balance to lock funds.")

                    # 4) Create and save the withdraw order
                    order = form.save(commit=False)
                    order.buyer_offer = offer_locked
                    order.seller = request.user
                    order.save()

                    # 5) Update the offer's available amount and deactivate if empty
                    offer_locked.amount_available -= amount
                    if offer_locked.amount_available <= 0:
                        offer_locked.is_active = False
                    offer_locked.save()

                messages.success(request, f"Order #{order.id} placed successfully!")
                return redirect('sell_order_details', order.id)

            except ValidationError as e:
                messages.error(request, e.message)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # GET: instantiate blank form with buy_offer & user for widget attrs
        form = WithdrawOrderForm(buy_offer=offer, user=request.user)

    return render(request, 'p2p/create_withdraw_order.html', {
        'form': form,
        'offer': offer,
    })


@login_required
def sell_order_details(request, order_id):
    """Show a SellOrder’s details to the seller and the merchant buyer-offer owner."""
    order = get_object_or_404(WithdrawOrder, id=order_id)

    # Only the seller who created it or the merchant who posted the BuyOffer can see it
    if request.user != order.seller and request.user != order.buyer_offer.merchant:
        return HttpResponseForbidden("You are not authorized to view this order.")

    return render(request, "p2p/sell_order_details.html", {"order": order})


@user_passes_test(lambda u: u.is_superuser)  # Ensure only admins can access
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect("home")  # Redirect non-admins
    
    sell_asset_total_orders        = AssetSellOrder.objects.count()
    pending_orders      = AssetSellOrder.objects.filter(status="pending").count()
    awaiting_conf       = AssetSellOrder.objects.filter(status="awaiting_confirmation").count()
    completed_orders    = AssetSellOrder.objects.filter(status="completed").count()


    total_orders        = DepositOrder.objects.count()
    pending_orders      = DepositOrder.objects.filter(status="pending").count()
    completed_orders    = DepositOrder.objects.filter(status="completed").count()
    disputed_orders     = DepositOrder.objects.filter(status="disputed").count()

    total_disputes      = Dispute.objects.count()
    pending_disputes    = Dispute.objects.filter(status="pending").count()
    resolved_buyer      = Dispute.objects.filter(status="resolved_buyer").count()
    resolved_merchant   = Dispute.objects.filter(status="resolved_merchant").count()

    recent_orders       = DepositOrder.objects.order_by("-created_at")[:5]
    recent_disputes     = Dispute.objects.order_by("-created_at")[:5]

    # Orders awaiting credit, with proof joined
    raw_orders = (AssetSellOrder.objects
                  .filter(status="awaiting_confirmation")
                  .select_related(None)  # no FK except .user
                  .prefetch_related("proof"))  # pulls PaymentProof
    to_credit_orders = []
    for order in raw_orders.order_by("created_at"):
        cost_ngn = (order.amount_asset * order.rate_ngn).quantize(Decimal('0.01'))
        order.profit = (order.amount_ngn - cost_ngn).quantize(Decimal('0.01'))
        order.proof_url = order.proof.image.url if hasattr(order, 'proof') else None


        # # Try to get the related proof
        # try:
        #     proof = order.proof  # use related_name
        #     order.proof_url = proof.image.url
        #     print(f"[✅ Proof Found] Order ID: {order.id}, Proof URL: {order.proof_url}")
        # except PaymentProof.DoesNotExist:
        #     order.proof_url = None
        #     print(f"[❌ No Proof] Order ID: {order.id}")


        to_credit_orders.append(order)


    return render(request, "p2p/admin_dashboard.html", {
        "total_orders": total_orders,
        "sell_asset_total_orders": sell_asset_total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "disputed_orders": disputed_orders,
        "total_disputes": total_disputes,
        "pending_disputes": pending_disputes,
        "resolved_buyer": resolved_buyer,
        "resolved_merchant": resolved_merchant,
        "recent_orders": recent_orders,
        "recent_disputes": recent_disputes,

        "to_credit_orders": to_credit_orders,
        "awaiting_confirmation": awaiting_conf,
    })
    

@login_required
def dashboard(request):
    wallet = Wallet.objects.get(user=request.user)
    
    total_orders = DepositOrder.objects.filter(buyer=request.user).count()
    total_sales = DepositOrder.objects.filter(sell_offer__merchant=request.user, status="completed").count()
    merchant_total_orders = DepositOrder.objects.filter(sell_offer__merchant=request.user).count()
    open_disputes = Dispute.objects.filter(order__buyer=request.user, status="pending").count()
    purchase_history = CryptoPurchase.objects.filter(user=request.user).order_by('-created_at')

    if request.user.is_merchant:
        total_orders = DepositOrder.objects.filter(sell_offer__merchant=request.user).count()
    else:
        total_orders = DepositOrder.objects.filter(buyer=request.user).count()

    if request.user.is_merchant:
        recent_orders = DepositOrder.objects.filter(sell_offer__merchant=request.user).order_by("-created_at")[:5]
    else:
        recent_orders = DepositOrder.objects.filter(buyer=request.user).order_by("-created_at")[:5]

    context = {
        "wallet": wallet,
        "total_orders": total_orders,
        "total_sales": total_sales,
        "merchant_total_orders": merchant_total_orders,
        "open_disputes": open_disputes,
        "recent_orders": recent_orders,
        "purchase_history": purchase_history
    }

    return render(request, "p2p/dashboard.html", context)


@login_required
def marketplace(request):
    """Display all active sell/buy offers from merchants with total completed orders."""
    # Buy offers (Withdraw_P2P_Offer) - no change needed since fiat is off-platform
    withdraw = Withdraw_P2P_Offer.objects.filter(is_active=True).select_related('merchant').order_by('-created_at')
    
    # Sell offers (Deposit_P2P_Offer)
    deposit_qs = Deposit_P2P_Offer.objects.filter(is_available=True).select_related('merchant').annotate(
        merchant_total_orders=Count(
            'orders',
            filter=Q(orders__status='completed')
        )
    ).order_by('-created_at')
    
    # Add effective_max_amount to each sell offer
    for offer in deposit_qs:
        available_balance = offer.merchant.wallet.balance
        offer.effective_max_amount = min(offer.max_amount, available_balance)
    
    return render(request, "p2p/marketplace.html", {"deposit": deposit_qs, "withdraw": withdraw})


@login_required
def order_details(request, order_id):
    """Show order details to buyer and merchant."""
    order = get_object_or_404(DepositOrder, id=order_id)

    # Restrict access: Only the buyer or merchant can view the order
    if request.user != order.buyer and request.user != order.sell_offer.merchant:
        return HttpResponseForbidden("You are not authorized to view this order.")

    return render(request, "p2p/order_details.html", {"order": order})

@login_required
def order_details_partial(request, order_id):
    order = get_object_or_404(DepositOrder, pk=order_id)  # replace with actual model
    if request.user not in [order.buyer, order.sell_offer.merchant]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    context = {'order': order, 'request': request}
    status_html = render_to_string('partials/_status_block.html', context)
    buttons_html = render_to_string('partials/_button_block.html', context)

    return JsonResponse({
        'status_html': status_html,
        'buttons_html': buttons_html,
    })


@require_POST
def mark_as_paid(request, order_id):
    order = get_object_or_404(DepositOrder, id=order_id)
    if request.user != order.buyer:
        return JsonResponse({"error": "Unauthorized"}, status=403)
    if order.status != 'pending':
        return JsonResponse({"error": "Order is not pending"}, status=400)
    
    order.status = 'paid'
    order.save(update_fields=["status"])
    
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"order_{order.id}",
        {
            "type": "order_status_update",
            "data": {
                "event": "paid",
                "status": "paid",
                "order_id": order.id
            }
        }
    )
    return JsonResponse({"success": True, "message": "You have marked the order as paid."})

@user_passes_test(lambda u: u.is_superuser)
def update_order_status(request, order_id):
    order = get_object_or_404(DepositOrder, id=order_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['pending', 'paid', 'completed', 'cancelled']:
            order.status = new_status
            order.save(update_fields=['status'])
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"order_{order.id}",
                {
                    "type": "order_status_update",
                    "data": {
                        "event": new_status,
                        "status": new_status,
                        "order_id": order.id
                    }
                }
            )
            return JsonResponse({"success": True, "message": f"Order status updated to {new_status}"})
    return JsonResponse({"error": "Invalid request"}, status=400)

@login_required
@require_POST
def release_fund(request, order_id):
    order = get_object_or_404(DepositOrder, id=order_id)
    if request.user != order.sell_offer.merchant:
        return JsonResponse({"error": "Unauthorized"}, status=403)
    if order.status != "paid":
        return JsonResponse({"error": "Order is not ready for release"}, status=400)
    
    merchant_wallet = Wallet.objects.get(user=request.user)
    buyer_wallet = Wallet.objects.get(user=order.buyer)
    if not merchant_wallet.release_funds(order.amount_requested):
        return JsonResponse({"error": "Insufficient locked funds"}, status=400)
    
    buyer_wallet.deposit(order.amount_requested)
    order.status = "completed"
    order.save(update_fields=["status"])
    
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"order_{order.id}",
        {
            "type": "order_status_update",
            "data": {
                "event": "completed",
                "status": "completed",
                "order_id": order.id
            }
        }
    )
    return JsonResponse({"message": "Funds released to buyer. Order completed."})



@login_required
@require_POST
def merchant_confirm_sell(request, order_id):
    """
    Merchant acknowledges they’ve paid the seller off-chain.
    We only bump status from 'pending' → 'paid'; no wallet changes here.
    """
    so = get_object_or_404(WithdrawOrder, id=order_id, buyer_offer__merchant=request.user)

    if so.status != 'pending':
        return JsonResponse({"error": "Order cannot be marked paid."}, status=400)

    so.status = 'paid'
    so.save(update_fields=['status'])

    return JsonResponse({"message": f"Order #{so.id} marked as paid. Waiting on seller to release tokens."})


@login_required
@require_POST
def seller_confirm_release(request, order_id):
    """Allow the seller (user) to release locked tokens to the merchant after merchant has paid off-chain."""
    so = get_object_or_404(WithdrawOrder, id=order_id)

    # Only the seller can release their tokens
    if request.user != so.seller or so.status != 'paid':
        return JsonResponse({"error": "Unauthorized or invalid state"}, status=403)

    seller_wallet   = Wallet.objects.get(user=so.seller)
    merchant_wallet = Wallet.objects.get(user=so.buyer_offer.merchant)

    # transfer escrowed tokens
    if seller_wallet.transfer_escrow(so.buyer_offer.merchant, so.amount_requested):
        so.status = 'completed'
        so.save(update_fields=['status'])
        return JsonResponse({"message": f"Tokens released! Order #{so.id} completed."})
    else:
        return JsonResponse({"error": "Unable to release tokens"}, status=400)


@login_required
def create_dispute(request, order_id):
    """Allow a buyer to raise a dispute for an order."""
    order = get_object_or_404(DepositOrder, id=order_id, buyer=request.user)

    if hasattr(order, "dispute"):  # Check if a dispute already exists
        messages.error(request, "A dispute has already been raised for this order.")
        return redirect("order_details", order_id=order.id)

    if request.method == "POST":
        form = DisputeForm(request.POST, request.FILES)
        if form.is_valid():
            dispute = form.save(commit=False)
            dispute.order = order
            dispute.buyer = request.user
            dispute.save()

            # Send notification emails
            merchant_email = order.sell_offer.merchant.email
            admin_email = User.objects.filter(is_superuser=True).values_list("email", flat=True)

            send_mail(
                subject="New Dispute Raised",
                message=f"A dispute has been raised for Order #{order.id} by {request.user.username}.",
                from_email="noreply@zunhub.com",
                recipient_list=[merchant_email] + list(admin_email),
                fail_silently=True,
            )

            messages.success(request, "Dispute submitted successfully. The merchant and admin have been notified.")
            return redirect("order_details", order_id=order.id)

    else:
        print("Dispute form page loaded")  # Debugging
        form = DisputeForm()

    return render(request, "p2p/create_dispute.html", {"form": form, "order": order})

@login_required
def cancel_dispute(request, dispute_id):
    dispute = get_object_or_404(Dispute, id=dispute_id, buyer=request.user)

    if dispute.status == "pending":
        # Refund locked funds back to merchant
        merchant_wallet = Wallet.objects.get(user=dispute.order.sell_offer.merchant)
        merchant_wallet.refund_funds(dispute.order.amount_requested)
        dispute.delete()
        messages.success(request, "Dispute has been canceled and funds refunded to merchant.")
    else:
        messages.error(request, "You cannot cancel this dispute.")

    return redirect("order_details", order_id=dispute.order.id)

@login_required
def track_dispute(request, dispute_id):
    """Allows the buyer (or admin) to track dispute progress."""
    dispute = get_object_or_404(Dispute, id=dispute_id)

    if request.user != dispute.buyer and not request.user.is_superuser:
        messages.error(request, "You do not have permission to view this dispute.")
        return redirect("order_details", order_id=dispute.order.id)

    return render(request, "p2p/track_dispute.html", {"dispute": dispute})


@login_required
def dispute_list(request):
    """Show disputes related to the logged-in user (as buyer or merchant)."""
    disputes = (
        Dispute.objects.filter(order__buyer=request.user) |
        Dispute.objects.filter(order__sell_offer__merchant=request.user)
    ).order_by("-created_at")

    return render(request, "p2p/dispute_list.html", {"disputes": disputes})


@login_required
def buyer_orders(request):
    # 1. User bought tokens
    buy_qs = DepositOrder.objects.filter(buyer=request.user).annotate(
        order_type=Value('buy', output_field=CharField())
    )
    # 2. User sold tokens
    sell_qs = WithdrawOrder.objects.filter(seller=request.user).annotate(
        order_type=Value('sell', output_field=CharField())
    )

    # Merge and paginate
    all_orders = sorted(
        chain(buy_qs, sell_qs),
        key=lambda o: o.created_at,
        reverse=True
    )
    paginator = Paginator(all_orders, 5)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Aggregates
    total_orders    = len(all_orders)
    total_amount    = sum(o.total_price for o in all_orders) or 0
    total_completed = sum(1 for o in all_orders if o.status == 'completed')
    total_disputed  = sum(1 for o in all_orders if o.status == 'disputed')
    total_pending   = sum(1 for o in all_orders if o.status == 'pending')
    total_paid      = sum(1 for o in all_orders if o.status == 'paid')

    return render(request, 'p2p/buyer_orders.html', {
        'page_obj': page_obj,
        'total_orders': total_orders,
        'total_amount': total_amount,
        'total_completed': total_completed,
        'total_disputed': total_disputed,
        'total_pending': total_pending,
        'total_paid': total_paid,
    })



@login_required
def merchant_orders(request):
    # 1. Users selling to merchant
    sell_qs = WithdrawOrder.objects.filter(buyer_offer__merchant=request.user).annotate(
        order_type=Value('sell', output_field=CharField())
    )
    # 2. Merchant selling to users
    buy_qs = DepositOrder.objects.filter(sell_offer__merchant=request.user).annotate(
        order_type=Value('buy', output_field=CharField())
    )
    # merge into a single list, sorted by created_at
    p2p_orders = sorted(
        chain(sell_qs, buy_qs),
        key=lambda o: o.created_at,
        reverse=True
    )
    paginator = Paginator(p2p_orders, 10)  # 10 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Now do Python-based aggregates on the list
    total_orders     = len(p2p_orders)
    total_amount     = sum(o.total_price for o in p2p_orders) or 0
    total_completed  = sum(1 for o in p2p_orders if o.status == 'completed')
    total_disputed   = sum(1 for o in p2p_orders if o.status == 'disputed')
    total_pending    = sum(1 for o in p2p_orders if o.status == 'pending')
    total_paid       = sum(1 for o in p2p_orders if o.status == 'paid')

    return render(request, "p2p/merchant_orders.html", {
        'p2p_orders':       p2p_orders,
        'total_orders':     total_orders,
        'total_amount':     total_amount,
        'total_completed':  total_completed,
        'total_disputed':   total_disputed,
        'total_pending':    total_pending,
        'total_paid':       total_paid,
        'page_obj':         page_obj,
    })



