from ninja import Schema
from typing import Optional
from datetime import datetime, date


class ProductSchema(Schema):
    """
    Schema for Product
    """
    id: Optional[int] = None
    product_category_id: Optional[int]  # Category ID
    product_name: str
    product_image: Optional[str] = None  # Image URL will be passed
    product_description: Optional[str] = None
    product_price: float
    product_upcoming: Optional[bool] = False


class ProductCreateSchema(Schema):
    """
    Input schema for creating/updating a Product (excludes product_image which is uploaded as file)
    """
    product_category_id: Optional[int] = None
    product_name: str
    product_description: Optional[str] = None
    product_price: float
    product_upcoming: Optional[bool] = False


class ProductVariantSchema(Schema):
    """
    Schema for Product Variant
    """
    id: Optional[int] = None
    product_id: int  # Product ID
    product_variant_price: float
    product_variant_size: Optional[str] = None
    product_variant_name: str
    product_variant_order: Optional[int] = 0
    product_variant_type: Optional[str] = None


class CategorySchema(Schema):
    category_name: str

class ProductDetailsSchema(Schema):
    product_meatcut: Optional[str]
    product_weight: Optional[float]
    product_packaging: Optional[str]
    product_origin: Optional[str]
    product_processing: Optional[str]

class ProductDiscountSchema(Schema):
    discount_percentage: Optional[float]
    discount_start_date: Optional[datetime]
    discount_end_date: Optional[datetime]
    discount_code: Optional[str]
    discount_type: Optional[str]

class CouponSchema(Schema):
    coupon_code: Optional[str]
    coupon_discount: Optional[float]
    coupon_start_date: Optional[date]
    coupon_end_date: Optional[date]
    coupon_is_expired: Optional[bool] = False