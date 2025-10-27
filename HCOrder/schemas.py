from ninja import Schema
from typing import Optional
from datetime import date, time, datetime

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

