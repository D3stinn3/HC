from ninja import Schema
from typing import Optional
from datetime import date, time

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

