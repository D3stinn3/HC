import uuid
from django.utils.timezone import now

def upload_to(instance, filename):
    """
    Generate a unique file path for storing media files in AWS S3.
    """
    file_extension = filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"

    if hasattr(instance, 'user') and instance.user:
        return f"uploads/{instance.user.id}/{now().strftime('%Y%m%d')}/{unique_filename}"
    return f"uploads/anonymous/{now().strftime('%Y%m%d')}/{unique_filename}"
