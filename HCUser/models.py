from django.db import models
from .image_util import upload_to
from django.contrib.auth.models import AbstractUser


# Create your models here.
class HomeChoiceUser(AbstractUser):
    email = models.EmailField(max_length=255, unique=True)
    avatar = models.ImageField(upload_to=upload_to, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    biography = models.CharField(max_length=255, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    clerkId = models.CharField(max_length=255, null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.username