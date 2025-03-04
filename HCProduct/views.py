from django.shortcuts import render
from django.shortcuts import render
from ninja_extra import NinjaExtraAPI, api_controller, http_get
from ninja_extra.permissions import IsAuthenticated
from .schemas import ProductSchema, ProductVariantSchema, CategorySchema
from HCProduct.models import Product, Category, ProductVariant
from django.contrib.auth import authenticate, logout, login
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_jwt.controller import TokenObtainPairController
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
# from django.core.cache import caches
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from ninja_jwt.authentication import JWTAuth
from HCUser.utils.permission_auth_util import ClerkAuthenticationPermission
from HCUser.utils.auth_util import clerk_authenticated

"""NinjaExtra API FOR HomeChoice"""

"""Initialize API"""

api = NinjaExtraAPI(urls_namespace='productapi')

api.register_controllers(NinjaJWTDefaultController)

# Create your views here.

# csrf_cache = caches["default"]

"""Get All Products"""

@api.get("/products", tags=["products"])
def get_products(request):
    """
    Retrieve all products.
    """
    products = Product.objects.all()
    product_list = [
        {
            "id": product.id,
            "product_name": product.product_name,
            "product_category": product.product_category.category_name if product.product_category else None,
            "product_image": product.product_image.url if product.product_image else None,
            "product_description": product.product_description,
            "product_price": product.product_price,
            "product_upcoming": product.product_upcoming,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
        }
        for product in products
    ]
    return JsonResponse({"success": True, "data": product_list})

"""Get Products by Category"""

@api.get("/products/category/{category_slug}", tags=["products"])
def get_products_by_category(request, category_slug: str):
    """
    Retrieve all products belonging to a specific category.
    """
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(product_category=category)

    product_list = [
        {
            "id": product.id,
            "product_name": product.product_name,
            "product_image": product.product_image.url if product.product_image else None,
            "product_description": product.product_description,
            "product_price": product.product_price,
            "product_upcoming": product.product_upcoming,
        }
        for product in products
    ]
    return JsonResponse({"success": True, "category": category.category_name, "data": product_list})

"""Get Product Variants by Product"""

@api.get("/product/{product_id}/variants", tags=["product_variants"])
def get_product_variants(request, product_id: int):
    """
    Retrieve all variants of a given product.
    """
    product = get_object_or_404(Product, id=product_id)
    variants = ProductVariant.objects.filter(product=product)

    variant_list = [
        {
            "id": variant.id,
            "product_variant_name": variant.product_variant_name,
            "product_variant_size": variant.product_variant_size,
            "product_variant_price": variant.product_variant_price,
            "product_variant_order": variant.product_variant_order,
            "product_variant_type": variant.product_variant_type,
        }
        for variant in variants
    ]
    return JsonResponse({"success": True, "product": product.product_name, "data": variant_list})

"""Create Product"""

@api.post("/products", tags=["products"])
def create_product(request, payload: ProductSchema):
    """
    Create a new product.
    """
    category = get_object_or_404(Category, id=payload.product_category_id) if payload.product_category_id else None
    product = Product.objects.create(
        product_category=category,
        product_name=payload.product_name,
        product_description=payload.product_description,
        product_price=payload.product_price,
        product_upcoming=payload.product_upcoming,
    )
    return JsonResponse({"success": True, "message": "Product created successfully", "product_id": product.id})

