from django.db import models
from HCUser.models import HomeChoiceUser
from HCProduct.models import Product, ProductVariant

# Create your models here.

class Cart(models.Model):
    user = models.ForeignKey(HomeChoiceUser, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

    def total_price(self):
        """
        Calculates total price of all cart items.
        """
        return sum(item.total_item_price() for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.product_name if self.product else self.variant.product_variant_name}"

    def total_item_price(self):
        """
        Calculates total price for this item.
        """
        price = self.variant.product_variant_price if self.variant else self.product.product_price
        return self.quantity * price