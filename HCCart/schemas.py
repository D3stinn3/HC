from ninja import Schema
from typing import Optional

class CartItemSchema(Schema):
    product_id: Optional[int] = None  # Either product_id or variant_id is required
    variant_id: Optional[int] = None
    quantity: int


class CartSchema(Schema):
    user_id: int
    items: list[CartItemSchema]
