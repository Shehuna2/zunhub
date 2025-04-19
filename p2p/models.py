from django.db import models
from django.conf import settings
# from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.translation import gettext_lazy as _



# class User(AbstractUser):
#     is_merchant = models.BooleanField(default=False)  # Merchant flag

#     def __str__(self):
#         role = "Merchant" if self.is_merchant else "Regular User"
#         return f"{self.username} - {role}"

# class UserProfile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
#     full_name = models.CharField(max_length=100, blank=True, null=True)
#     account_no = models.CharField(max_length=20, blank=True, null=True)
#     bank_name = models.CharField(max_length=100, blank=True, null=True)

#     def __str__(self):
#         return f"Profile of {self.user.username}"
    

class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    locked_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def lock_funds(self, amount):
        """Move funds into escrow (locked balance)"""
        if self.balance >= amount:
            self.balance -= amount
            self.locked_balance += amount
            self.save()
            return True
        return False    # insuffient funds
    
    def release_funds(self, amount):
        """Release funds from escrow to the buyer"""
        if self.locked_balance >= amount:
            self.locked_balance -= amount
            self.save()
            return True
        return False
    
    def refund_funds(self, amount):
        """Return escrowed funds back to the merchant"""
        if self.locked_balance >= amount:
            self.locked_balance -= amount
            self.balance += amount
            self.save()
            return True
        return False # Nothing to return
    
    def deposit(self, amount):
        """Add funds to the wallet."""
        if amount > 0:
            self.balance += amount
            self.save()

    def withdraw(self, amount):
        """Remove funds from the wallet if enough balance exists."""
        if amount > 0 and self.balance >= amount:
            self.balance -= amount
            self.save()
            return True
        return False  # Insufficient balance
    
    def can_withdraw(self, amount):
        """Check if a user can withdraw given the balance and disputes."""
        active_disputes = Dispute.objects.filter(order__merchant=self.user, status="pending").exists()
        return self.balance - self.locked_balance >= amount and not active_disputes
    

    def __str__(self):
        return f"{self.user.username} - Balance: ₦{self.balance}, Locked: ₦{self.locked_balance}"

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_wallet(sender, instance, created, **kwargs):
    """Automatically create a wallet for new users."""
    if created:
        Wallet.objects.create(user=instance)


class SellOffer(models.Model):
    merchant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount_available = models.DecimalField(max_digits=10, decimal_places=2)  # Merchant balance
    min_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_amount = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        wallet = Wallet.objects.get(user=self.merchant)
        max_allowed = wallet.balance - wallet.locked_balance # Ensure no over-allocation
        if self.max_amount > max_allowed:
            self.max_amount = max_allowed  
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.merchant.username} - ₦{self.price_per_unit} per unit (Min: ₦{self.min_amount}, Max: ₦{self.max_amount})"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Awaiting Payment'),
        ('paid', 'Paid - Releasing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    sell_offer = models.ForeignKey(SellOffer, on_delete=models.CASCADE)
    amount_requested = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.total_price = self.amount_requested * self.sell_offer.price_per_unit
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.id} - {self.buyer.username} from {self.sell_offer.merchant.username}"


class Dispute(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("resolved_buyer", "Resolved in Buyer's Favor"),
        ("resolved_merchant", "Resolved in Merchant's Favor"),
        ("rejected", "Rejected"),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="dispute")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="disputes_raised")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reason = models.TextField(blank=True, null=True)
    proof = models.FileField(upload_to="disputes/", blank=True, null=True)
    admin_comment = models.TextField(blank=True, null=True)  # Admin’s decision notes
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def resolve_dispute(self, decision, admin_comment=""):
        self.status = decision
        self.admin_comment = admin_comment
        self.resolved_at = timezone.now()
        self.save()

        if decision == "resolved_buyer":
            self.order.buyer.wallet.balance += self.order.amount_requested
            decision_text = "in Buyer's favor"
        elif decision == "resolved_merchant":
            self.order.merchant.wallet.balance += self.order.amount_requested
            decision_text = "in Merchant's favor"
        else:
            decision_text = "Rejected"

        self.order.status = "completed" if decision != "rejected" else "disputed"
        self.order.save()

        send_mail(
            "Dispute Resolution",
            f"Your dispute for Order #{self.order.id} has been resolved {decision_text}.\nAdmin Comment: {self.admin_comment}",
            "noreply@zunhub.com",
            [self.order.buyer.email, self.order.merchant.email],
            fail_silently=True,
        )

