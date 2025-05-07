from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from ninja_extra import NinjaExtraAPI
from ninja import Schema
from typing import Optional
from datetime import datetime
from django.utils import timezone

from HCUser.models import HomeChoiceUser
from HCProduct.models import Product
from .models import Order
from .schemas import OrderSchema, OrderOutSchema

api = NinjaExtraAPI(urls_namespace='orderapi')

"""Get All Orders"""
@api.get("/orders", tags=["orders"])
def get_all_orders(request):
    """
    Retrieve all orders.
    """
    orders = Order.objects.select_related("user", "product").all()
    data = [
        {
            "id": order.id,
            "user_id": order.user.id,
            "product_id": order.product.id,
            "product_name": order.product.product_name,
            "order_price": order.order_price,
            "status": order.status,
            "order_date": order.order_date,
            "order_time": order.order_time,
            "created_at": order.created_at,
        }
        for order in orders
    ]
    return JsonResponse({"success": True, "data": data})

"""Get Order By ID"""
@api.get("/orders/{order_id}", tags=["orders"])
def get_order_by_id(request, order_id: int):
    """
    Retrieve a single order by its ID.
    """
    order = get_object_or_404(Order, id=order_id)
    return JsonResponse({
        "success": True,
        "data": {
            "id": order.id,
            "user_id": order.user.id,
            "product_id": order.product.id,
            "product_name": order.product.product_name,
            "order_price": order.order_price,
            "status": order.status,
            "order_date": order.order_date,
            "order_time": order.order_time,
            "created_at": order.created_at,
        }
    })

"""Create Order By Product ID"""

@api.post("/orders", tags=["orders"])
def create_order(request, payload: OrderSchema):
    """
    Create a new order based on product.
    """
    user = request.user  # Ensure user is authenticated
    product = get_object_or_404(Product, id=payload.product_id)

    order = Order.objects.create(
        user=user,
        product=product,
        order_price=payload.order_price,
        status=payload.status or 'pending',
        order_date=payload.order_date or timezone.now().date(),
        order_time=payload.order_time or timezone.now().time()
    )

    return JsonResponse({"success": True, "message": "Order created", "order_id": order.id})

"""Update Order By ID"""

@api.put("/orders/{order_id}", tags=["orders"])
def update_order(request, order_id: int, payload: OrderSchema):
    """
    Update an order.
    """
    order = get_object_or_404(Order, id=order_id)
    product = get_object_or_404(Product, id=payload.product_id)

    order.product = product
    order.order_price = payload.order_price
    order.status = payload.status or order.status
    order.order_date = payload.order_date or order.order_date
    order.order_time = payload.order_time or order.order_time
    order.save()

    return JsonResponse({"success": True, "message": "Order updated successfully"})


"""Delete Order"""

@api.delete("/orders/{order_id}", tags=["orders"])
def delete_order(request, order_id: int):
    """
    Delete an order.
    """
    order = get_object_or_404(Order, id=order_id)
    order.delete()
    return JsonResponse({"success": True, "message": "Order deleted successfully"})

"""Get Orders By User ID"""

@api.get("/orders/user/clerk/{clerk_id}", tags=["orders"])
def get_orders_by_clerk_id(request, clerk_id: str):
    """
    Retrieve all orders made by a user using their Clerk ID.
    """
    user = get_object_or_404(HomeChoiceUser, clerkId=clerk_id)
    orders = Order.objects.filter(user=user)

    data = [
        {
            "id": order.id,
            "product_id": order.product.id,
            "product_name": order.product.product_name,
            "order_price": order.order_price,
            "status": order.status,
            "order_date": order.order_date,
            "order_time": order.order_time,
            "created_at": order.created_at,
        }
        for order in orders
    ]
    return JsonResponse({"success": True, "clerk_id": clerk_id, "data": data})
