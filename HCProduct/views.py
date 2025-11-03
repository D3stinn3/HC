from django.shortcuts import render
from django.shortcuts import render
from ninja_extra import NinjaExtraAPI, api_controller, http_get
from ninja_extra.permissions import IsAuthenticated
from .schemas import ProductSchema, ProductCreateSchema, ProductVariantSchema, CategorySchema,ProductDetailsSchema, ProductDiscountSchema, CouponSchema
from HCCart.schemas import CartItemSchema, CartSchema
from HCProduct.models import Product, Category, ProductVariant, productDetails, ProductDiscount, Coupon
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
import json
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from typing import Any, Optional, List, Dict
from ninja import NinjaAPI, Form, Schema, File, UploadedFile

"""NinjaExtra API FOR HomeChoice"""

"""Initialize API"""

api = NinjaExtraAPI(urls_namespace='productapi')

api.register_controllers(NinjaJWTDefaultController)

# Create your views here.

"""Get All Products"""

@api.get("/products", tags=["products"])
def get_all_products(request):
    """
    Retrieve all products including their details and discounts.
    """
    products = Product.objects.prefetch_related('details', 'discounts').select_related('product_category').all()

    product_list = []
    for product in products:
        # Fetch related product details
        details = product.details.all()
        details_list = [
            {
                "id": detail.id,
                "product_meatcut": detail.product_meatcut,
                "product_weight": detail.product_weight,
                "product_packaging": detail.product_packaging,
                "product_origin": detail.product_origin,
                "product_processing": detail.product_processing,
            }
            for detail in details
        ]

        # Fetch related product discounts
        discounts = product.discounts.all()
        discounts_list = [
            {
                "id": discount.id,
                "discount_percentage": discount.discount_percentage,
                "discount_start_date": discount.discount_start_date,
                "discount_end_date": discount.discount_end_date,
                "discount_code": discount.discount_code,
                "discount_type": discount.discount_type,
            }
            for discount in discounts
        ]

        product_list.append({
            "id": product.id,
            "product_name": product.product_name,
            "product_category": product.product_category.category_name if product.product_category else None,
            "product_image": (product.product_image.url if getattr(product, "product_image", None) and hasattr(product.product_image, "url") else (str(product.product_image) if product.product_image else None)),
            "product_description": product.product_description,
            "product_price": product.product_price,
            "product_upcoming": product.product_upcoming,
            "created_at": product.created_at,
            "details": details_list,
            "discounts": discounts_list,
        })

    return JsonResponse({"success": True, "data": product_list})


"""Get Products By ID"""

@api.get("/products/{product_id}", tags=["products"])
def get_product(request, product_id: int):
    """
    Retrieve product details by ID.
    """
    product = get_object_or_404(Product, id=product_id)
    
    # Fetch product details
    product_details = product.details.all()
    details_list = [
        {
            "id": detail.id,
            "product_meatcut": detail.product_meatcut,
            "product_weight": detail.product_weight,
            "product_packaging": detail.product_packaging,
            "product_origin": detail.product_origin,
            "product_processing": detail.product_processing,
        }
        for detail in product_details
    ]

    # Fetch product discounts
    product_discounts = product.discounts.all()
    discounts_list = [
        {
            "id": discount.id,
            "discount_percentage": discount.discount_percentage,
            "discount_start_date": discount.discount_start_date,
            "discount_end_date": discount.discount_end_date,
            "discount_code": discount.discount_code,
            "discount_type": discount.discount_type,
        }
        for discount in product_discounts
    ]

    return JsonResponse({
        "success": True,
        "data": {
            "id": product.id,
            "product_name": product.product_name,
            "product_category": product.product_category.category_name if product.product_category else None,
            "product_image": (product.product_image.url if getattr(product, "product_image", None) and hasattr(product.product_image, "url") else (str(product.product_image) if product.product_image else None)),
            "product_description": product.product_description,
            "product_price": product.product_price,
            "product_upcoming": product.product_upcoming,
            "created_at": product.created_at,
            "details": details_list,
            "discounts": discounts_list,
        }
    })
    
"""Create Product Details"""
@api.post("/products/{product_id}/details", tags=["product_details"])
def create_product_details(request, product_id: int, payload: ProductDetailsSchema):
    product = get_object_or_404(Product, id=product_id)
    detail = productDetails.objects.create(
        product=product,
        product_meatcut=payload.product_meatcut,
        product_weight=payload.product_weight,
        product_packaging=payload.product_packaging,
        product_origin=payload.product_origin,
        product_processing=payload.product_processing,
    )
    return JsonResponse({"success": True, "message": "Product details created", "detail_id": detail.id})

# ==========================
# Get a Single Product Detail
# ==========================
@api.get("/products/{product_id}/details", tags=["product_details"])
def get_product_details_by_product(request, product_id: int):
    product = get_object_or_404(Product, id=product_id)
    details = product.details.all()

    details_list = [
        {
            "id": detail.id,
            "product_meatcut": detail.product_meatcut,
            "product_weight": detail.product_weight,
            "product_packaging": detail.product_packaging,
            "product_origin": detail.product_origin,
            "product_processing": detail.product_processing,
        }
        for detail in details
    ]

    return JsonResponse({"success": True, "product_id": product.id, "details": details_list})


# ==========================
# Update a Product Detail
# ==========================
@api.put("/products/{product_id}/details", tags=["product_details"])
def update_product_details_by_product(request, product_id: int, payload: ProductDetailsSchema):
    product = get_object_or_404(Product, id=product_id)
    try:
        detail = product.details.first()
        if not detail:
            return JsonResponse({"success": False, "message": "No product details found to update."}, status=404)
    except productDetails.DoesNotExist:
        return JsonResponse({"success": False, "message": "No product details found to update."}, status=404)

    detail.product_meatcut = payload.product_meatcut
    detail.product_weight = payload.product_weight
    detail.product_packaging = payload.product_packaging
    detail.product_origin = payload.product_origin
    detail.product_processing = payload.product_processing
    detail.save()

    return JsonResponse({"success": True, "message": "Product details updated successfully"})


# ==========================
# Delete a Product Detail
# ==========================
@api.delete("/products/{product_id}/details", tags=["product_details"])
def delete_product_details_by_product(request, product_id: int):
    product = get_object_or_404(Product, id=product_id)
    details = product.details.all()

    if not details.exists():
        return JsonResponse({"success": False, "message": "No product details found to delete."}, status=404)

    details.delete()

    return JsonResponse({"success": True, "message": "All product details deleted successfully"})



"""Create Product Discount"""
@api.post("/products/{product_id}/discounts", tags=["product_discounts"])
def create_product_discount(request, product_id: int, payload: ProductDiscountSchema):
    product = get_object_or_404(Product, id=product_id)
    discount = ProductDiscount.objects.create(
        product=product,
        discount_percentage=payload.discount_percentage,
        discount_start_date=payload.discount_start_date,
        discount_end_date=payload.discount_end_date,
        discount_code=payload.discount_code,
        discount_type=payload.discount_type,
    )
    return JsonResponse({"success": True, "message": "Product discount created", "discount_id": discount.id})
from HCProduct.models import ProductDiscount
from .schemas import ProductDiscountSchema

# ==========================
# Get a Single Product Discount
# ==========================
@api.get("/product/discounts/{discount_id}", tags=["product_discounts"])
def get_product_discount(request, discount_id: int):
    discount = get_object_or_404(ProductDiscount, id=discount_id)
    
    return JsonResponse({
        "success": True,
        "data": {
            "id": discount.id,
            "product": discount.product.id,
            "discount_percentage": discount.discount_percentage,
            "discount_start_date": discount.discount_start_date,
            "discount_end_date": discount.discount_end_date,
            "discount_code": discount.discount_code,
            "discount_type": discount.discount_type,
        }
    })

# ==========================
# Update a Product Discount
# ==========================
@api.put("/product/discounts/{discount_id}", tags=["product_discounts"])
def update_product_discount(request, discount_id: int, payload: ProductDiscountSchema):
    discount = get_object_or_404(ProductDiscount, id=discount_id)
    
    discount.discount_percentage = payload.discount_percentage
    discount.discount_start_date = payload.discount_start_date
    discount.discount_end_date = payload.discount_end_date
    discount.discount_code = payload.discount_code
    discount.discount_type = payload.discount_type
    discount.save()

    return JsonResponse({"success": True, "message": "Product discount updated successfully"})

# ==========================
# Delete a Product Discount
# ==========================
@api.delete("/product/discounts/{discount_id}", tags=["product_discounts"])
def delete_product_discount(request, discount_id: int):
    discount = get_object_or_404(ProductDiscount, id=discount_id)
    discount.delete()
    return JsonResponse({"success": True, "message": "Product discount deleted successfully"})

"""Create a Coupon"""
@api.post("/coupons", tags=["coupons"])
def create_coupon(request, payload: CouponSchema):
    coupon = Coupon.objects.create(
        coupon_code=payload.coupon_code,
        coupon_discount=payload.coupon_discount,
        coupon_start_date=payload.coupon_start_date,
        coupon_end_date=payload.coupon_end_date,
        coupon_is_expired=payload.coupon_is_expired
    )
    return JsonResponse({"success": True, "message": "Coupon created", "coupon_id": coupon.id})


"""Get all Coupons"""
@api.get("/coupons", tags=["coupons"])
def get_all_coupons(request):
    coupons = Coupon.objects.all()
    coupon_list = [
        {
            "id": coupon.id,
            "coupon_code": coupon.coupon_code,
            "coupon_discount": coupon.coupon_discount,
            "coupon_start_date": coupon.coupon_start_date,
            "coupon_end_date": coupon.coupon_end_date,
            "coupon_is_expired": coupon.coupon_is_expired,
        }
        for coupon in coupons
    ]
    return JsonResponse({"success": True, "data": coupon_list})



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
            "product_image": default_storage.url(product.product_image) if product.product_image else None,
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
        "product_image": (product.product_image.url if getattr(product, "product_image", None) and hasattr(product.product_image, "url") else (str(product.product_image) if product.product_image else None)),
        "product_description": product.product_description,
        "product_price": product.product_price,
        "product_upcoming": product.product_upcoming,
    }

    return JsonResponse({"success": True, "product": product_data})


"""Create Product"""

@api.post("/products", tags=["products"])
def create_product(request, payload: ProductCreateSchema = Form(...), file: Optional[UploadedFile] = File(None)):
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


@api.put("/products/{product_id}", tags=["products"])
def update_product(
    request,
    product_id: int,
    product_category_id: Optional[int] = Form(None),
    product_name: Optional[str] = Form(None),
    product_description: Optional[str] = Form(None),
    product_price: Optional[float] = Form(None),
    product_upcoming: Optional[bool] = Form(None),
    file: Optional[UploadedFile] = File(None),
):
    """
    Update an existing product with a new image if provided.
    """
    product = get_object_or_404(Product, id=product_id)

    # Fallback: if no form fields were parsed (likely JSON request), parse JSON body
    if (
        product_category_id is None
        and product_name is None
        and product_description is None
        and product_price is None
        and product_upcoming is None
        and not file
    ):
        try:
            body_text = request.body.decode("utf-8") if hasattr(request, "body") else None
            if body_text:
                data = json.loads(body_text)
                product_category_id = data.get("product_category_id", product_category_id)
                product_name = data.get("product_name", product_name)
                product_description = data.get("product_description", product_description)
                product_price = data.get("product_price", product_price)
                product_upcoming = data.get("product_upcoming", product_upcoming)
        except Exception:
            pass

    # Update Image on S3 if a new file is provided
    if file:
        file_name = f"products/{request.user.id}/{uuid.uuid4()}_{file.name}"
        save_path = default_storage.save(file_name, file)
        product.product_image = save_path

    if product_category_id:
        category = get_object_or_404(Category, id=product_category_id)
        product.product_category = category

    if product_name is not None:
        product.product_name = product_name
    if product_description is not None:
        product.product_description = product_description
    if product_price is not None:
        product.product_price = product_price
    if product_upcoming is not None:
        product.product_upcoming = product_upcoming
    product.save()

    # Return updated snapshot including image URL (if set)
    image_url = None
    try:
        if getattr(product, "product_image", None) and hasattr(product.product_image, "url"):
            image_url = product.product_image.url
    except Exception:
        image_url = None

    return JsonResponse({
        "success": True,
        "message": "Product updated successfully",
        "data": {
            "id": product.id,
            "product_name": product.product_name,
            "product_description": product.product_description,
            "product_price": product.product_price,
            "product_upcoming": product.product_upcoming,
            "product_category": product.product_category.id if product.product_category else None,
            "product_image": image_url,
        },
    })


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

"""Get Category By ID"""
@api.get("/categories/{category_id}", tags=["categories"])
def get_category_by_id(request, category_id: int):
    """
    Retrieve a category by its ID.
    """
    category = get_object_or_404(Category, id=category_id)

    return JsonResponse({
        "success": True,
        "data": {
            "id": category.id,
            "category_name": category.category_name,
            "category_image": default_storage.url(str(category.category_image)) if category.category_image else None,
            "slug": category.slug,
            "created_at": category.created_at,
            "updated_at": category.updated_at,
        }
    })



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





