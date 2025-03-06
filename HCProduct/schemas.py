from ninja import Schema
from typing import Optional


# class CategorySchema(Schema):
#     """
#     Schema for Category
#     """
#     id: Optional[int] = None
#     category_name: str
#     slug: Optional[str] = None
#     category_image: Optional[str] = None  # Assuming image URL will be passed


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