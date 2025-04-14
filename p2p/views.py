from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from django.http import HttpResponseForbidden, JsonResponse
from django.contrib import messages
from .forms import UserRegisterForm, OrderForm, DisputeForm, SellOfferForm
from decimal import Decimal
from .models import Wallet, SellOffer, Order, Dispute
from gasfee.models import CryptoPurchase



def merchant_required(function):
    return user_passes_test(lambda u: hasattr(u, 'is_merchant') and u.is_merchant)(function)

@merchant_required
@login_required
def create_sell_offer(request):
    if request.method == "POST":
        form = SellOfferForm(request.POST, user=request.user)
        if form.is_valid():
            sell_offer = form.save(commit=False)
            sell_offer.merchant = request.user
            sell_offer.save()
            messages.success(request, "Sell offer created successfully.")
            return redirect("dashboard")  # Adjust to your desired redirect URL
    else:
        form = SellOfferForm(user=request.user)
    return render(request, "p2p/create_sell_offer.html", {"form": form})


@user_passes_test(lambda u: u.is_superuser)  # Ensure only admins can access
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect("home")  # Redirect non-admins

    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status="pending").count()
    completed_orders = Order.objects.filter(status="completed").count()
    disputed_orders = Order.objects.filter(status="disputed").count()

    total_disputes = Dispute.objects.count()
    pending_disputes = Dispute.objects.filter(status="pending").count()
    resolved_buyer = Dispute.objects.filter(status="resolved_buyer").count()
    resolved_merchant = Dispute.objects.filter(status="resolved_merchant").count()

    recent_orders = Order.objects.order_by("-created_at")[:5]
    recent_disputes = Dispute.objects.order_by("-created_at")[:5]

    context = {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "disputed_orders": disputed_orders,
        "total_disputes": total_disputes,
        "pending_disputes": pending_disputes,
        "resolved_buyer": resolved_buyer,
        "resolved_merchant": resolved_merchant,
        "recent_orders": recent_orders,
        "recent_disputes": recent_disputes,
    }
    
    return render(request, "p2p/admin_dashboard.html", context)


@login_required
def dashboard(request):
    wallet = Wallet.objects.get(user=request.user)
    
    total_orders = Order.objects.filter(buyer=request.user).count()
    total_sales = Order.objects.filter(sell_offer__merchant=request.user, status="completed").count()
    merchant_total_orders = Order.objects.filter(sell_offer__merchant=request.user).count()
    open_disputes = Dispute.objects.filter(order__buyer=request.user, status="pending").count()
    purchase_history = CryptoPurchase.objects.filter(user=request.user).order_by('-created_at')

    if request.user.is_merchant:
        total_orders = Order.objects.filter(sell_offer__merchant=request.user).count()
    else:
        total_orders = Order.objects.filter(buyer=request.user).count()

    if request.user.is_merchant:
        recent_orders = Order.objects.filter(sell_offer__merchant=request.user).order_by("-created_at")[:5]
    else:
        recent_orders = Order.objects.filter(buyer=request.user).order_by("-created_at")[:5]

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


User = get_user_model()

def merchant_list(request):
    merchants = User.objects.filter(is_merchant=True)
    return render(request, "p2p/merchants.html", {"merchants": merchants})


def marketplace(request):
    """Display all active sell offers from merchants."""
    offers = SellOffer.objects.filter(is_available=True).order_by('-created_at')
    return render(request, "p2p/marketplace.html", {"offers": offers})


@login_required
def order_details(request, order_id):
    """Show order details to buyer and merchant."""
    order = get_object_or_404(Order, id=order_id)

    # Restrict access: Only the buyer or merchant can view the order
    if request.user != order.buyer and request.user != order.sell_offer.merchant:
        return HttpResponseForbidden("You are not authorized to view this order.")

    return render(request, "p2p/order_details.html", {"order": order})


@login_required
def create_order(request, offer_id):
    """Buyer requests an order from a merchant."""
    sell_offer = get_object_or_404(SellOffer, id=offer_id, is_available=True)
    merchant_wallet = Wallet.objects.get(user=sell_offer.merchant)

    if request.method == "POST":
        form = OrderForm(request.POST, sell_offer=sell_offer)
        if form.is_valid():
            order = form.save(commit=False)
            order.buyer = request.user
            order.sell_offer = sell_offer  # ✅ Ensure sell_offer is set
            order.save()
            messages.success(request, "Order created! Please make payment to the merchant.")
            return redirect("order_details", order.id)
        else:
            messages.error(request, "Invalid order details. Please check and try again.")

    else:
        form = OrderForm(sell_offer=sell_offer)

    return render(request, "p2p/create_order.html", {"form": form, "sell_offer": sell_offer})


@login_required
def mark_as_paid(request, order_id):
    """Allows the buyer to mark an order as paid."""
    order = get_object_or_404(Order, id=order_id)

    if request.user != order.buyer:
        return HttpResponseForbidden("You are not authorized to update this order.")

    if order.status == 'pending':
        order.status = 'paid'
        order.save()
        messages.success(request, "You have marked the order as paid. Please wait for the merchant to confirm.")
    else:
        messages.error(request, "This order cannot be marked as paid.")

    return redirect('order_details', order_id=order.id)


@login_required
def confirm_payment(request, order_id): 
    """Merchant confirms payment and releases internal currency."""
    order = get_object_or_404(Order, id=order_id, sell_offer__merchant=request.user)

    if order.status == "paid":
        # Access balances through the UserProfile model
        merchant_wallet = Wallet.objects.get(user=request.user)
        buyer_wallet = Wallet.objects.get(user=order.buyer)

        if merchant_wallet.balance >= order.amount_requested:  # Use the correct field name
            merchant_wallet.balance -= order.amount_requested
            buyer_wallet.balance += order.amount_requested
            merchant_wallet.save()
            buyer_wallet.save()

            # Mark order as completed
            order.status = "completed"
            order.save()

            return JsonResponse({"message": "Payment confirmed. Internal currency released to buyer."})
        else:
            return JsonResponse({"error": "Insufficient balance"}, status=400)

    return JsonResponse({"error": "Invalid action"}, status=400)


@login_required
def create_dispute(request, order_id):
    """Allow a buyer to raise a dispute for an order."""
    order = get_object_or_404(Order, id=order_id, buyer=request.user)

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
        dispute.delete()
        messages.success(request, "Dispute has been canceled successfully.")
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
    disputes = Dispute.objects.filter(
        order__buyer=request.user
    ) | Dispute.objects.filter(
        order__merchant=request.user
    ).order_by("-created_at")

    return render(request, "p2p/dispute_list.html", {"disputes": disputes})

@login_required
def buyer_orders(request):
    """Show all orders placed by the buyer."""
    orders = Order.objects.filter(buyer=request.user).order_by('-created_at')
    return render(request, "p2p/buyer_orders.html", {"orders": orders})

@login_required
def merchant_orders(request):
    """Show all orders received by the merchant."""
    orders = Order.objects.filter(sell_offer__merchant=request.user).order_by('-created_at')
    return render(request, "p2p/merchant_orders.html", {"orders": orders})

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserRegisterForm()
    return render(request, 'p2p/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
    return render(request, 'p2p/login.html')

def user_logout(request):
    logout(request)
    return redirect('login')

@login_required
def update_bank_details(request):
    """Allows users to update their bank account details."""
    profile = request.user.profile  # Access UserProfile

    if request.method == "POST":
        profile.account_no = request.POST.get("account_no")
        profile.bank_name = request.POST.get("bank_name")
        profile.save()

        messages.success(request, "Bank details updated successfully.")
        return redirect("update_bank_details")

    return render(request, "p2p/update_bank_details.html", {"profile": profile})


