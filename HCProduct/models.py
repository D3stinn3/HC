from django.db import models
from HCUser.utils.image_util import upload_to
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone

# Create your models here.

class Category(models.Model):
    category_name = models.CharField(max_length=100, null=True, blank=True)
    slug = models.SlugField(unique=True, null=True, blank=True)
    category_image = models.ImageField(upload_to=upload_to, null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self) -> str:
        return self.category_name
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.category_name)
        super(Category, self).save(*args, **kwargs)
    
class Product(models.Model):
    product_category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    product_name = models.CharField(max_length=100, null=True, blank=True)
    product_image = models.ImageField(upload_to=upload_to, null=True, blank=True)
    product_description = models.TextField(null=True, blank=True)
    product_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    product_upcoming = models.BooleanField(default=False)
    product_rating = models.DecimalField(max_digits=100, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self) -> str:
        return self.product_name
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.product_name)
        super(Product, self).save(*args, **kwargs)

class productDetails(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='details')
    product_meatcut = models.CharField(max_length=100,null=True, blank=True)
    product_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    product_packaging = models.CharField(max_length=100, null=True, blank=True)
    product_origin = models.CharField(max_length=100, null=True, blank=True)
    product_processing = models.CharField(max_length=100, null=True, blank=True)

    
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    product_variant_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    product_variant_size = models.CharField(max_length=100, null=True, blank=True)
    product_variant_name = models.CharField(max_length=100, null=True, blank=True)
    product_variant_order = models.IntegerField(default=0, null=True, blank=True)
    product_variant_type = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self) -> str:
        return self.product_variant_name
    
    def save(self, *args, **kwargs):
        if not self.product_variant_name and self.product:
            self.product_variant_name = slugify(self.product.product_name)
        super(ProductVariant, self).save(*args, **kwargs)
            
class Coupon(models.Model):
    coupon_code = models.CharField(max_length=100, null=True, blank=True)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    coupon_start_date = models.DateField(null=True, blank=True)
    coupon_end_date = models.DateField(null=True, blank=True)
    coupon_is_expired = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
        