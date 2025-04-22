from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import UserRegisterForm, ProfileForm

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('edit_profile')  
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
    return render(request, 'accounts/login.html')

def user_logout(request):
    logout(request)
    return redirect('login')


@login_required
def profile_view(request):
    user = request.user
    profile = user.profile
    return render(request, 'accounts/profile.html', {'user': user, 'profile': profile})

@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('dashboard')  # or any named URL
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'accounts/edit_profile.html', {'form': form})


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

    return render(request, "accounts/update_bank_details.html", {"profile": profile})
