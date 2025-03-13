from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib import messages
from .forms import UserRegisterForm, OrderForm
from decimal import Decimal
from .models import Wallet, SellOffer, Order


@login_required
def wallet_dashboard(request):
    wallet = Wallet.objects.get(user=request.user)
    return render(request, 'p2p/dashboard.html', {'wallet': wallet})

@login_required
def deposit(request):
    if request.method == "POST":
        amount = float(request.POST.get("amount"))
        wallet = Wallet.objects.get(user=request.user)
        wallet.deposit(amount)
        messages.success(request, f"Deposited ₦{amount} successfully!")
    return render(request, "p2p/deposit.html")

@login_required
def withdraw(request):
    if request.method == "POST":
        amount = float(request.POST.get("amount"))
        wallet = Wallet.objects.get(user=request.user)
        if wallet.withdraw(amount):
            messages.success(request, f"Withdrawn ₦{amount} successfully!")
        else:
            messages.error(request, "Insufficient balance!")
    return render(request, "p2p/withdraw.html")

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

def dashboard(request):
    return render(request, 'p2p/dashboard.html')

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
