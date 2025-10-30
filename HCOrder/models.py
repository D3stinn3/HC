from django.db import models
from django.utils import timezone
from HCUser.models import HomeChoiceUser
from HCProduct.models import Product
import json

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(HomeChoiceUser, on_delete=models.CASCADE, related_name='orders')
    payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, related_name='orders', null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # Address snapshots captured at checkout time to avoid drift
    shipping_address = models.TextField(null=True, blank=True)
    billing_address = models.TextField(null=True, blank=True)
    order_date = models.DateField(default=timezone.now)
    order_time = models.TimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

    def get_total_amount(self):
        """Calculate total from order items"""
        return sum(item.total_price() for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # Snapshot of selected weight/variant at checkout (e.g., "500g", "1kg")
    weight_variant = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity}x {self.product.product_name} - Order #{self.order.id}"

    def total_price(self):
        """Calculate total price for this item"""
        return self.quantity * self.price


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


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20, null=True, blank=True)
    to_status = models.CharField(max_length=20)
    reason = models.TextField(null=True, blank=True)
    changed_by = models.ForeignKey(HomeChoiceUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_status_changes')
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.order_id}: {self.from_status} -> {self.to_status}"


# Auto-log status transitions without actor/reason (those can be supplied by views where available)
from django.db.models.signals import pre_save
from django.dispatch import receiver


@receiver(pre_save, sender=Order)
def log_order_status_change(sender, instance: Order, **kwargs):
    if not instance.pk:
        # New order, log creation as pending -> current if different
        OrderStatusHistory.objects.create(
            order=instance,
            from_status=None,
            to_status=instance.status,
        )
        return

    try:
        previous = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return

    if previous.status != instance.status:
        OrderStatusHistory.objects.create(
            order=instance,
            from_status=previous.status,
            to_status=instance.status,
        )


class Refund(models.Model):
    REFUND_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refunds')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    reason = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='pending')
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Refund #{self.id} - Order {self.order_id} - {self.status}"


class Shipment(models.Model):
    SHIPMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='shipments')
    carrier = models.CharField(max_length=100, null=True, blank=True)
    tracking_number = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=SHIPMENT_STATUS_CHOICES, default='pending')
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Shipment #{self.id} - Order {self.order_id} - {self.status}"


class ShipmentItem(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='items')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='shipment_items')
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ShipmentItem #{self.id} - Shipment {self.shipment_id}"


class APILog(models.Model):
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField(null=True, blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    user_id = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    request_body = models.TextField(null=True, blank=True)
    response_body = models.TextField(null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['endpoint']),
            models.Index(fields=['status_code']),
        ]

    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.status_code} - {self.created_at}"

