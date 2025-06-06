from django.shortcuts import render
from django.shortcuts import render
from django.shortcuts import render
from ninja_extra import NinjaExtraAPI, api_controller, http_get
from ninja_extra.permissions import IsAuthenticated
from .schemas import CartItemSchema, CartSchema
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

from django.contrib.auth.decorators import login_required
from HCCart.models import CheckoutSession, Cart
from HCCart.schemas import CheckoutSessionCreateSchema, CheckoutSessionOutSchema
import uuid

"""NinjaExtra API FOR HomeChoice"""

"""Initialize API"""

api = NinjaExtraAPI(urls_namespace='cartapi')

api.register_controllers(NinjaJWTDefaultController)

# Create your views here.

# csrf_cache = caches["default"]

"""Get User Cart"""

@api.get("/cart", tags=["cart"])
def get_cart(request):
    """
    Retrieve the cart details for the logged-in user.
    """
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()

    cart_data = {
        "cart_id": cart.id,
        "total_price": cart.total_price(),
        "items": [
            {
                "cart_item_id": item.id,
                "product_name": item.product.product_name if item.product else item.variant.product_variant_name,
                "quantity": item.quantity,
                "unit_price": item.variant.product_variant_price if item.variant else item.product.product_price,
                "total_price": item.total_item_price()
            }
            for item in cart_items
        ]
    }

    return JsonResponse({"success": True, "data": cart_data})

"""Clear Cart"""

@api.delete("/cart/clear", tags=["cart"])
def clear_cart(request):
    """
    Clear all items in the cart.
    """
    cart = get_object_or_404(Cart, user=request.user)
    cart.items.all().delete()

    return JsonResponse({"success": True, "message": "Cart cleared."})

"""Create Checkout Session"""

@api.post("/cart/checkout", tags=["cart"])
def create_checkout_session(request, payload: CheckoutSessionCreateSchema):
    """
    Initiate a checkout session for the user's cart.
    """
    cart = get_object_or_404(Cart, id=payload.cart_id, user=request.user)

    if not cart.items.exists():
        return JsonResponse({"success": False, "message": "Cart is empty."}, status=400)

    if hasattr(cart, 'checkout_session') and cart.checkout_session.status == 'pending':
        return JsonResponse({
            "success": False,
            "message": "Checkout session already exists.",
            "reference": cart.checkout_session.reference
        }, status=400)

    reference = f"HC-{uuid.uuid4().hex[:10].upper()}"

    session = CheckoutSession.objects.create(
        cart=cart,
        user=request.user,
        clerk_id=request.user.clerkId or "",
        reference=reference,
        amount=payload.amount,
        status="pending"
    )

    session_data = {
        "id": session.id,
        "cart_id": session.cart.id,
        "user_id": session.user.id,
        "clerk_id": session.clerk_id,
        "reference": session.reference,
        "amount": float(session.amount),
        "status": session.status,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }

    return JsonResponse({"success": True, "data": session_data})


