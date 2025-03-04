from django.db import models
from .utils.image_util import upload_to
from django.contrib.auth.models import AbstractUser
from django.urls import reverse

from .managers import CustomUserManager

# Create your models here.
class HomeChoiceUser(AbstractUser):
    email = models.EmailField(max_length=255, unique=True)
    avatar = models.ImageField(upload_to=upload_to, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    biography = models.CharField(max_length=255, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    clerkId = models.CharField(max_length=255, null=True, blank=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        ordering = ["-date_joined"]
    
    def __str__(self):
        return self.username
    
class ShippingAddress(models.Model):
    user = models.ForeignKey(HomeChoiceUser, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    street = models.CharField(max_length=100, null=True, blank=True)
    street_number = models.CharField(max_length=10, null=True, blank=True)
    zip_code = models.CharField(max_length=30, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    shipping_phone_number = models.CharField(max_length=20, null=True, blank=True)
    current_address = models.BooleanField(default=False, null=True, blank=True)

    def __str__(self):
        return f'{self.street}, {self.street_number}, {self.city}, {self.country}, {self.zip_code}, {self.shipping_phone_number}'

    def get_absolute_url(self):
        return reverse('shipping-address')