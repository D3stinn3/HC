from django.db import models
from utils import upload_to
from django.contrib.auth.models import AbstractUser


# Create your models here.
class HomeChoiceUser(AbstractUser):
    email = models.EmailField(max_length=255, unique=True)
    avatar = models.ImageField(upload_to=upload_to, null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']