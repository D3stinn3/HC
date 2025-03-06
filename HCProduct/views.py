from django.shortcuts import render
from django.shortcuts import render
from ninja_extra import NinjaExtraAPI, api_controller, http_get
from ninja_extra.permissions import IsAuthenticated
from .schemas import ProductSchema, ProductVariantSchema, CategorySchema
from HCCart.schemas import CartItemSchema, CartSchema
from HCProduct.models import Product, Category, ProductVariant
from HCCart.models import Cart, CartItem
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
import uuid
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from typing import Any, Optional, List, Dict
from ninja import NinjaAPI, Form, Schema, File, UploadedFile

"""NinjaExtra API FOR HomeChoice"""

"""Initialize API"""

api = NinjaExtraAPI(urls_namespace='productapi')

api.register_controllers(NinjaJWTDefaultController)

# Create your views here.

# csrf_cache = caches["default"]

"""Get All Products"""

# @api.get("/products", tags=["products"])
# def get_products(request):
#     """
#     Retrieve all products.
#     """
#     products = Product.objects.all()
#     product_list = [
#         {
#             "id": product.id,
#             "product_name": product.product_name,
#             "product_category": product.product_category.category_name if product.product_category else None,
#             "product_image": product.product_image.url if product.product_image else None,
#             "product_description": product.product_description,
#             "product_price": product.product_price,
#             "product_upcoming": product.product_upcoming,
#             "created_at": product.created_at,
#             "updated_at": product.updated_at,
#         }
#         for product in products
#     ]
#     return JsonResponse({"success": True, "data": product_list})

@api.get("/products", tags=["products"])
def get_all_products(request):
    """
    Retrieve all products.
    """
    products = Product.objects.all()
    product_list = [
        {
            "id": product.id,
            "product_name": product.product_name,
            "product_category": product.product_category.category_name if product.product_category else None,
            "product_image": default_storage.url(product.product_image) if product.product_image else None,
            "product_description": product.product_description,
            "product_price": product.product_price,
            "product_upcoming": product.product_upcoming,
            "created_at": product.created_at,
        }
        for product in products
    ]
    return JsonResponse({"success": True, "data": product_list})

"""Get Products By ID"""

@api.get("/products/{product_id}", tags=["products"])
def get_product(request, product_id: int):
    """
    Retrieve product details by ID.
    """
    product = get_object_or_404(Product, id=product_id)

    return JsonResponse({
        "success": True,
        "data": {
            "id": product.id,
            "product_name": product.product_name,
            "product_category": product.product_category.category_name if product.product_category else None,
            "product_image": default_storage.url(product.product_image) if product.product_image else None,
            "product_description": product.product_description,
            "product_price": product.product_price,
            "product_upcoming": product.product_upcoming,
            "created_at": product.created_at,
        }
    })



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

"""Get Product by Variant"""

@api.get("/product/variant/{variant_id}", tags=["product_variants"])
def get_product_by_variant(request, variant_id: int):
    """
    Retrieve product details by variant ID.
    """
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product = variant.product

    product_data = {
        "id": product.id,
        "product_name": product.product_name,
        "product_category": product.product_category.category_name if product.product_category else None,
        "product_image": product.product_image.url if product.product_image else None,
        "product_description": product.product_description,
        "product_price": product.product_price,
        "product_upcoming": product.product_upcoming,
    }

    return JsonResponse({"success": True, "product": product_data})


"""Create Product"""

# @api.post("/products", tags=["products"])
# def create_product(request, payload: ProductSchema):
#     """
#     Create a new product.
#     """
#     category = get_object_or_404(Category, id=payload.product_category_id) if payload.product_category_id else None
#     product = Product.objects.create(
#         product_category=category,
#         product_name=payload.product_name,
#         product_description=payload.product_description,
#         product_price=payload.product_price,
#         product_upcoming=payload.product_upcoming,
#     )
#     return JsonResponse({"success": True, "message": "Product created successfully", "product_id": product.id})

@api.post("/products", tags=["products"])
def create_product(request, payload: ProductSchema, file: Optional[UploadedFile] = None):
    """
    Create a new product with an image uploaded to AWS S3.
    """
    user = request.user  # Assuming authentication is required

    save_path = None
    if file:
        file_name = f"products/{user.id}/{uuid.uuid4()}_{file.name}"
        save_path = default_storage.save(file_name, file)  # Uploads to S3

    category = get_object_or_404(Category, id=payload.product_category_id) if payload.product_category_id else None
    product = Product.objects.create(
        product_category=category,
        product_name=payload.product_name,
        product_description=payload.product_description,
        product_price=payload.product_price,
        product_upcoming=payload.product_upcoming,
        product_image=save_path  # Stores S3 URL
    )

    return JsonResponse({"success": True, "message": "Product created successfully", "product_id": product.id})



"""Update Product"""

# @api.put("/products/{product_id}", tags=["products"])
# def update_product(request, product_id: int, payload: ProductSchema):
#     """
#     Update an existing product.
#     """
#     product = get_object_or_404(Product, id=product_id)

#     if payload.product_category_id:
#         category = get_object_or_404(Category, id=payload.product_category_id)
#         product.product_category = category

#     product.product_name = payload.product_name
#     product.product_description = payload.product_description
#     product.product_price = payload.product_price
#     product.product_upcoming = payload.product_upcoming
#     product.save()

#     return JsonResponse({"success": True, "message": "Product updated successfully"})

@api.put("/products/{product_id}", tags=["products"])
def update_product(request, product_id: int, payload: ProductSchema, file: Optional[UploadedFile] = File(None)):
    """
    Update an existing product with a new image if provided.
    """
    product = get_object_or_404(Product, id=product_id)

    # Update Image on S3 if a new file is provided
    if file:
        file_name = f"products/{request.user.id}/{uuid.uuid4()}_{file.name}"
        save_path = default_storage.save(file_name, file)
        product.product_image = save_path

    if payload.product_category_id:
        category = get_object_or_404(Category, id=payload.product_category_id)
        product.product_category = category

    product.product_name = payload.product_name
    product.product_description = payload.product_description
    product.product_price = payload.product_price
    product.product_upcoming = payload.product_upcoming
    product.save()

    return JsonResponse({"success": True, "message": "Product updated successfully"})


"""Delete Product"""

@api.delete("/products/{product_id}", tags=["products"])
def delete_product(request, product_id: int):
    """
    Delete a product.
    """
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return JsonResponse({"success": True, "message": "Product deleted successfully"})


"""Create Product Variant API"""

@api.post("/products/{product_id}/variant", tags=["product_variants"])
def create_product_variant(request, product_id: int, payload: ProductVariantSchema):
    """
    Create a new product variant.
    """
    product = get_object_or_404(Product, id=product_id)

    variant = ProductVariant.objects.create(
        product=product,
        product_variant_price=payload.product_variant_price,
        product_variant_size=payload.product_variant_size,
        product_variant_name=payload.product_variant_name,
        product_variant_order=payload.product_variant_order,
        product_variant_type=payload.product_variant_type,
    )

    return JsonResponse({
        "success": True,
        "message": "Product variant created successfully",
        "variant_id": variant.id,
        "data": {
            "product_id": product.id,
            "product_name": product.product_name,
            "variant_id": variant.id,
            "variant_name": variant.product_variant_name,
            "variant_price": variant.product_variant_price,
            "variant_size": variant.product_variant_size,
            "variant_order": variant.product_variant_order,
            "variant_type": variant.product_variant_type,
            "created_at": variant.created_at,
        }
    })


"""Get Variants by Product"""

@api.get("/products/{product_id}/variants", tags=["product_variants"])
def get_variants_by_product(request, product_id: int):
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
    return JsonResponse({"success": True, "product": product.product_name, "variants": variant_list})




"""Update Product Variant"""

@api.put("/product/variant/{variant_id}", tags=["product_variants"])
def update_product_variant(request, variant_id: int, payload: ProductVariantSchema):
    """
    Update an existing product variant.
    """
    variant = get_object_or_404(ProductVariant, id=variant_id)

    variant.product_variant_price = payload.product_variant_price
    variant.product_variant_size = payload.product_variant_size
    variant.product_variant_name = payload.product_variant_name
    variant.product_variant_order = payload.product_variant_order
    variant.product_variant_type = payload.product_variant_type
    variant.save()

    return JsonResponse({"success": True, "message": "Product variant updated successfully"})

"""Delete Product Variant"""

@api.delete("/product/variant/{variant_id}", tags=["product_variants"])
def delete_product_variant(request, variant_id: int):
    """
    Delete a product variant.
    """
    variant = get_object_or_404(ProductVariant, id=variant_id)
    variant.delete()
    return JsonResponse({"success": True, "message": "Product variant deleted successfully"})


"""Add Product to Cart"""

@api.post("/cart/add", tags=["cart"])
@login_required
def add_to_cart(request, payload: CartItemSchema):
    """
    Add a product or product variant to the cart.
    """
    user = request.user  # Assuming authentication is in place
    cart, created = Cart.objects.get_or_create(user=user)

    product = None
    variant = None

    if payload.product_id:
        product = get_object_or_404(Product, id=payload.product_id)
    elif payload.variant_id:
        variant = get_object_or_404(ProductVariant, id=payload.variant_id)
    
    if not product and not variant:
        return JsonResponse({"success": False, "message": "Invalid product or variant."}, status=400)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, variant=variant, defaults={"quantity": payload.quantity}
    )

    if not created:
        cart_item.quantity += payload.quantity
        cart_item.save()

    return JsonResponse({
        "success": True,
        "message": "Product added to cart.",
        "cart_item_id": cart_item.id,
        "quantity": cart_item.quantity
    })
    
"""Remove Product from Cart"""

@api.delete("/cart/remove/{cart_item_id}", tags=["cart"])
@login_required
def remove_from_cart(request, cart_item_id: int):
    """
    Remove a product from the cart.
    """
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
    cart_item.delete()

    return JsonResponse({"success": True, "message": "Item removed from cart."})


"""Create Category API"""

@api.post("/categories", tags=["categories"])
def create_category(request, payload: CategorySchema, file: Optional[UploadedFile] = File(None)):
    """
    Create a new category with an optional image uploaded to AWS S3.
    """
    save_path = None
    if file:
        file_name = f"categories/{uuid.uuid4()}_{file.name}"
        save_path = default_storage.save(file_name, file)  # Upload to S3

    category = Category.objects.create(
        category_name=payload.category_name,
        category_image=save_path  # Save S3 URL if file exists
    )

    return JsonResponse({
        "success": True,
        "message": "Category created successfully",
        "category_id": category.id
    })
    
"""Get All Categories"""

# @api.get("/categories", tags=["categories"])
# def get_all_categories(request):
#     """
#     Retrieve all categories.
#     """
#     categories = Category.objects.all()
#     category_list = [
#         {
#             "id": category.id,
#             "category_name": category.category_name,
#             "category_image": default_storage.url(category.category_image) if category.category_image else None,
#             "created_at": category.created_at,
#         }
#         for category in categories
#     ]
#     return JsonResponse({"success": True, "data": category_list})

@api.get("/categories", tags=["categories"])
def get_all_categories(request):
    """
    Retrieve all categories.
    """
    categories = Category.objects.all()
    category_list = [
        {
            "id": category.id,
            "category_name": category.category_name,
            "category_image": default_storage.url(str(category.category_image)) if category.category_image else None,
            "created_at": category.created_at,
        }
        for category in categories
    ]
    return JsonResponse({"success": True, "data": category_list})


"""Update Category (Handles Image Upload)"""

@api.put("/categories/{category_id}", tags=["categories"])
def update_category(request, category_id: int, payload: CategorySchema, file: Optional[UploadedFile] = File(None)):
    """
    Update an existing category with a new image if provided.
    """
    category = get_object_or_404(Category, id=category_id)

    # Update Image on S3 if a new file is provided
    if file:
        file_name = f"categories/{uuid.uuid4()}_{file.name}"
        save_path = default_storage.save(file_name, file)
        category.category_image = save_path

    category.category_name = payload.category_name
    category.save()

    return JsonResponse({"success": True, "message": "Category updated successfully"})

"""Delete Category"""

@api.delete("/categories/{category_id}", tags=["categories"])
def delete_category(request, category_id: int):
    """
    Delete a category from the database.
    """
    category = get_object_or_404(Category, id=category_id)

    # Delete category image from S3 (if exists)
    if category.category_image:
        default_storage.delete(category.category_image)

    category.delete()
    return JsonResponse({"success": True, "message": "Category deleted successfully"})





