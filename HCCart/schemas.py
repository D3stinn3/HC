from ninja import Schema
from typing import Optional
from datetime import datetime

class CartItemSchema(Schema):
    product_id: Optional[int] = None  # Either product_id or variant_id is required
    variant_id: Optional[int] = None
    quantity: int


class CartSchema(Schema):
    user_id: int
    items: list[CartItemSchema]
    

class CheckoutSessionCreateSchema(Schema):
    cart_id: int
    amount: float

class CheckoutSessionOutSchema(Schema):
    id: int
    cart_id: int
    user_id: int
    clerk_id: Optional[str]
    reference: str
    amount: float
    status: str
    created_at: datetime
    updated_at: datetime
