
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, UserProfile

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "full_name",
            "account_no",
            "bank_name",
            "phone_number",
            "date_of_birth",
            "profile_image",
            "id_document",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "w-full rounded-lg border border-primary-300 p-3 focus:border-primary-500 focus:ring-1 focus:ring-primary-300"}),
            "account_no": forms.TextInput(attrs={"class": "w-full rounded-lg border border-primary-300 p-3 focus:border-primary-500 focus:ring-1 focus:ring-primary-300"}),
            "bank_name": forms.TextInput(attrs={"class": "w-full rounded-lg border border-primary-300 p-3 focus:border-primary-500 focus:ring-1 focus:ring-primary-300"}),
            "phone_number": forms.TextInput(attrs={"class": "w-full rounded-lg border border-primary-300 p-3 focus:border-primary-500 focus:ring-1 focus:ring-primary-300"}),
            "date_of_birth": forms.DateInput(attrs={"class": "w-full rounded-lg border border-primary-300 p-3 focus:border-primary-500 focus:ring-1 focus:ring-primary-300", "type": "date"}),
            "profile_image": forms.ClearableFileInput(attrs={"class": "w-full text-sm text-primary-600"}),
            "id_document": forms.ClearableFileInput(attrs={"class": "w-full text-sm text-primary-600"}),
        }

    def clean_account_no(self):
        acc = self.cleaned_data.get('account_no')
        if not acc.isdigit():
            raise forms.ValidationError("Account number must contain only digits.")
        return acc

    def clean_profile_image(self):
        img = self.cleaned_data.get('profile_image')
        if img and img.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Image file too large (max 2MB).")
        return img