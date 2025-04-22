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
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    account_no = models.CharField(max_length=20, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/', default='images/bnb-bnb-logo.png', blank=True, null=True)
    id_document = models.FileField(upload_to='documents/' , blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"