from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    is_merchant = models.BooleanField(default=False)  # Merchant flag

    def __str__(self):
        role = "Merchant" if self.is_merchant else "Regular User"
        return f"{self.username} - {role}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=100, blank=True, null=True)
    account_no = models.CharField(max_length=20, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"