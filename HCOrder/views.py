from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from ninja_extra import NinjaExtraAPI
from ninja import Schema
from typing import Optional
from datetime import datetime
from django.utils import timezone
import requests
import json
from decouple import config

from HCUser.models import HomeChoiceUser
from HCProduct.models import Product
from .models import Order, Payment
from .schemas import OrderSchema, OrderOutSchema, PaymentSchema, PaymentVerifySchema, PaymentOutSchema

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


# ========== PAYMENT APIs ==========

"""Create Payment"""

@api.post("/payments/create", tags=["payments"])
def create_payment(request, payload: PaymentSchema):
    """
    Create a payment record for an order.
    This should be called before initiating Paystack payment.
    """
    order = get_object_or_404(Order, id=payload.order_id)
    
    # Check if payment already exists for this order
    existing_payment = Payment.objects.filter(order=order).first()
    if existing_payment:
        return JsonResponse({
            "success": False,
            "message": "Payment already exists for this order",
            "payment_id": existing_payment.id
        }, status=400)

    payment = Payment.objects.create(
        order=order,
        clerk_id=payload.clerk_id or order.user.clerkId,
        paystack_reference=payload.paystack_reference,
        amount_paid=payload.amount_paid,
        currency=payload.currency or 'KES',
        payment_status=payload.payment_status or 'pending'
    )

    return JsonResponse({
        "success": True,
        "message": "Payment record created",
        "payment_id": payment.id,
        "data": {
            "id": payment.id,
            "order_id": payment.order.id,
            "paystack_reference": payment.paystack_reference,
            "amount_paid": float(payment.amount_paid),
            "payment_status": payment.payment_status
        }
    })


"""Verify Payment with Paystack"""

@api.post("/payments/verify", tags=["payments"])
def verify_payment(request, payload: PaymentVerifySchema):
    """
    Handle Paystack webhook and verify payment.
    This endpoint receives Paystack webhooks and updates payment status.
    """
    try:
        event = payload.event
        data = payload.data
        
        # Extract reference from Paystack data
        reference = data.get('reference')
        transaction_id = data.get('id')
        
        if not reference:
            return JsonResponse({
                "success": False,
                "message": "No reference found in webhook data"
            }, status=400)

        # Get payment by reference
        payment = get_object_or_404(Payment, paystack_reference=reference)
        
        # Store full Paystack response
        payment.set_paystack_response(data)
        payment.paystack_transaction_id = transaction_id
        
        # Verify with Paystack API
        paystack_secret_key = config('PAYSTACK_SECRET_KEY')
        verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {paystack_secret_key}"}
        
        response = requests.get(verify_url, headers=headers)
        
        if response.status_code == 200:
            paystack_data = response.json()
            
            if paystack_data['status'] and paystack_data['data']['status'] == 'success':
                # Payment successful
                payment.payment_status = 'success'
                payment.verified_at = timezone.now()
                payment.set_paystack_response(paystack_data['data'])
                
                # Update order status
                order = payment.order
                order.status = 'delivered'  # or whatever status you want
                order.payment = payment
                order.save()
                
            else:
                payment.payment_status = 'failed'
                payment.set_paystack_response(paystack_data['data'])
        
        payment.save()
        
        return JsonResponse({
            "success": True,
            "message": "Payment verified successfully",
            "payment_status": payment.payment_status,
            "order_status": payment.order.status
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error verifying payment: {str(e)}"
        }, status=500)


"""Get Payment by Order ID"""

@api.get("/payments/order/{order_id}", tags=["payments"])
def get_payment_by_order(request, order_id: int):
    """
    Get payment information for a specific order.
    """
    order = get_object_or_404(Order, id=order_id)
    payments = Payment.objects.filter(order=order)
    
    payment_list = []
    for payment in payments:
        payment_list.append({
            "id": payment.id,
            "order_id": payment.order.id,
            "clerk_id": payment.clerk_id,
            "paystack_reference": payment.paystack_reference,
            "paystack_transaction_id": payment.paystack_transaction_id,
            "amount_paid": float(payment.amount_paid),
            "currency": payment.currency,
            "payment_status": payment.payment_status,
            "verified_at": payment.verified_at,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at
        })
    
    return JsonResponse({
        "success": True,
        "order_id": order_id,
        "data": payment_list
    })


"""Get All Payments by Clerk ID"""

@api.get("/payments/clerk/{clerk_id}", tags=["payments"])
def get_payments_by_clerk(request, clerk_id: str):
    """
    Get all payment records for a specific user by Clerk ID.
    """
    payments = Payment.objects.filter(clerk_id=clerk_id).select_related('order')
    
    payment_list = []
    for payment in payments:
        payment_list.append({
            "id": payment.id,
            "order_id": payment.order.id,
            "product_name": payment.order.product.product_name,
            "order_price": float(payment.order.order_price),
            "paystack_reference": payment.paystack_reference,
            "paystack_transaction_id": payment.paystack_transaction_id,
            "amount_paid": float(payment.amount_paid),
            "currency": payment.currency,
            "payment_status": payment.payment_status,
            "verified_at": payment.verified_at,
            "created_at": payment.created_at
        })
    
    return JsonResponse({
        "success": True,
        "clerk_id": clerk_id,
        "data": payment_list
    })


"""Get All Payments"""

@api.get("/payments", tags=["payments"])
def get_all_payments(request):
    """
    Get all payment records (admin only recommended).
    """
    payments = Payment.objects.select_related('order').all()
    
    payment_list = []
    for payment in payments:
        payment_list.append({
            "id": payment.id,
            "order_id": payment.order.id,
            "clerk_id": payment.clerk_id,
            "paystack_reference": payment.paystack_reference,
            "paystack_transaction_id": payment.paystack_transaction_id,
            "amount_paid": float(payment.amount_paid),
            "currency": payment.currency,
            "payment_status": payment.payment_status,
            "verified_at": payment.verified_at,
            "created_at": payment.created_at
        })
    
    return JsonResponse({
        "success": True,
        "data": payment_list
    })


"""Update Payment Status"""

@api.put("/payments/{payment_id}/status", tags=["payments"])
def update_payment_status(request, payment_id: int, status: str):
    """
    Manually update payment status (admin only recommended).
    """
    payment = get_object_or_404(Payment, id=payment_id)
    
    if status not in ['pending', 'success', 'failed', 'refunded']:
        return JsonResponse({
            "success": False,
            "message": "Invalid payment status"
        }, status=400)
    
    payment.payment_status = status
    payment.save()
    
    return JsonResponse({
        "success": True,
        "message": "Payment status updated",
        "payment_id": payment.id,
        "status": payment.payment_status
    })
