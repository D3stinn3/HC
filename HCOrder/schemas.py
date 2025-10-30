from ninja import Schema
from typing import Optional, List
from datetime import date, time, datetime

class OrderItemSchema(Schema):
    product_id: int
    quantity: int
    price: float
    weight_variant: Optional[str] = None


class BulkOrderSchema(Schema):
    cart_items: List[OrderItemSchema]
    total_amount: float
    status: Optional[str] = "pending"
    shipping_address: Optional[str] = None


class OrderSchema(Schema):
    product_id: int
    order_price: float
    status: Optional[str] = "pending"
    order_date: Optional[date] = None
    order_time: Optional[time] = None

class OrderOutSchema(Schema):
    id: int
    user_id: int
    product_id: int
    order_price: float
    status: str
    order_date: date
    order_time: time
    created_at: date
class OrderUpdateSchema(Schema):
    status: Optional[str] = None
    order_date: Optional[date] = None
    order_time: Optional[time] = None
    shipping_address: Optional[str] = None
    billing_address: Optional[str] = None


class OrderItemCreateSchema(Schema):
    product_id: int
    quantity: int
    price: float
    weight_variant: Optional[str] = None


class OrderItemUpdateSchema(Schema):
    quantity: Optional[int] = None
    price: Optional[float] = None


class OrderStatusUpdateSchema(Schema):
    status: str
    reason: Optional[str] = None



class PaymentSchema(Schema):
    order_id: int
    paystack_reference: str
    amount_paid: float
    currency: Optional[str] = "KES"
    payment_status: Optional[str] = "pending"
    clerk_id: Optional[str] = None


class PaymentVerifySchema(Schema):
    event: str  # 'charge.success' or 'charge.failed'
    data: dict  # Paystack response data


class PaymentOutSchema(Schema):
    id: int
    order_id: int
    clerk_id: Optional[str]
    paystack_reference: str
    paystack_transaction_id: Optional[str]
    amount_paid: float
    currency: str
    payment_status: str
    verified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class RefundCreateSchema(Schema):
    payment_id: int
    amount: float
    currency: Optional[str] = "KES"
    reason: Optional[str] = None


class RefundOutSchema(Schema):
    id: int
    order_id: int
    payment_id: int
    amount: float
    currency: str
    reason: Optional[str]
    status: str
    processed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ShipmentItemInputSchema(Schema):
    order_item_id: int
    quantity: int


class ShipmentCreateSchema(Schema):
    order_id: int
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    status: Optional[str] = "pending"
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[ShipmentItemInputSchema]


class ShipmentUpdateSchema(Schema):
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    status: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None


class ShipmentOutSchema(Schema):
    id: int
    order_id: int
    carrier: Optional[str]
    tracking_number: Optional[str]
    status: str
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
