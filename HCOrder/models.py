from django.db import models
from django.utils import timezone
from HCUser.models import HomeChoiceUser
from HCProduct.models import Product
import json

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(HomeChoiceUser, on_delete=models.CASCADE, related_name='orders')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders')
    payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, related_name='orders', null=True, blank=True)
    order_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    order_date = models.DateField(default=timezone.now)
    order_time = models.TimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username} - {self.product.product_name}"


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    clerk_id = models.CharField(max_length=255, null=True, blank=True)
    paystack_reference = models.CharField(max_length=255, unique=True)
    paystack_transaction_id = models.CharField(max_length=255, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    paystack_response = models.TextField(null=True, blank=True)  # Store full JSON response
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.paystack_reference} - {self.payment_status}"

    def set_paystack_response(self, data):
        """Helper method to store Paystack response as JSON string"""
        self.paystack_response = json.dumps(data)

    def get_paystack_response(self):
        """Helper method to retrieve Paystack response as JSON"""
        if self.paystack_response:
            return json.loads(self.paystack_response)
        return None

