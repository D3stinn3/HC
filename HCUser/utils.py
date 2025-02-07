from django.utils.timezone import now

"""Upload Image Function"""

def upload_to(instance, filename):
    # Using UUID to avoid filename collision
    prefix = 'uploads/{user_id}/{date}/'.format(user_id=instance.user.id if hasattr(instance, 'user') else 'anonymous', date=now().strftime('%Y%m%d'))
    return '{prefix}{filename}'.format(prefix=prefix, filename=filename)