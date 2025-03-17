from django.core.mail import send_mail

def notify_users(subject, message, recipients):
    send_mail(
        subject=subject,
        message=message,
        from_email="noreply@zunhub.com",
        recipient_list=recipients,
        fail_silently=True,
    )
