from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile

@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        try:
            # Ensure profile exists before saving
            if hasattr(instance, 'profile'):
                instance.profile.save()
            else:
                # Create profile if it doesn't exist
                UserProfile.objects.create(user=instance)
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=instance)