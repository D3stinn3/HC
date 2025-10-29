from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from ninja_extra import NinjaExtraAPI
from ninja_extra.permissions import IsAuthenticated
from ninja_jwt.authentication import JWTAuth
from ninja import Schema
from typing import Optional
from datetime import datetime
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Sum
import requests
import json
from decouple import config
import hmac
import hashlib
import time

from HCUser.models import HomeChoiceUser
from HCProduct.models import Product
from .models import Order, Payment, OrderItem, Refund, Shipment, ShipmentItem, OrderStatusHistory, APILog
from .api_logger import log_api_call
from .schemas import (
    OrderSchema,
    OrderOutSchema,
    BulkOrderSchema,
    OrderItemSchema,
    PaymentSchema,
    PaymentVerifySchema,
    PaymentOutSchema,
    OrderUpdateSchema,
    OrderItemCreateSchema,
    OrderItemUpdateSchema,
    RefundCreateSchema,
    RefundOutSchema,
    ShipmentCreateSchema,
    ShipmentUpdateSchema,
    ShipmentOutSchema,
    OrderStatusUpdateSchema,
)

api = NinjaExtraAPI(urls_namespace='orderapi', auth=JWTAuth())

# Simple RBAC: staff/admin only
class IsStaff(Schema):
    pass

def require_staff(request):
    try:
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False) and (getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)):
            return True
    except Exception:
        pass
    return False
"""Webhook Logs (tail)"""

@api.get("/webhooks/logs", tags=["webhooks"])
def get_webhook_logs(request, limit: int = 100):
    if not require_staff(request):
        return JsonResponse({"success": False, "message": "Forbidden"}, status=403)
    try:
        from django.conf import settings
        import os
        log_path = os.path.join(getattr(settings, 'BASE_DIR', ''), 'logs', 'paystack_webhooks.log')
        lines = []
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f.readlines()[-limit:]:
                    try:
                        lines.append(json.loads(line))
                    except Exception:
                        continue
        return JsonResponse({"success": True, "data": lines})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


"""Get All Orders"""
@api.get("/orders", tags=["orders"])
def get_all_orders(request):
    """
    Retrieve all orders with their items.
    """
    orders = Order.objects.select_related("user").prefetch_related("items__product").all()
    data = []
    
    for order in orders:
        items = []
        for item in order.items.all():
            items.append({
                "order_item_id": item.id,
                "product_id": item.product.id,
                "product_name": item.product.product_name,
                "quantity": item.quantity,
                "price": float(item.price),
                "total": float(item.total_price())
            })
        
        data.append({
            "id": order.id,
            "user_id": order.user.id,
            "total_amount": float(order.total_amount) if order.total_amount else float(order.get_total_amount()),
            "status": order.status,
            "order_date": order.order_date,
            "order_time": order.order_time,
            "created_at": order.created_at,
            "items": items
        })
    
    return JsonResponse({"success": True, "data": data})


"""Get Order Status History"""

@api.get("/orders/{order_id}/history", tags=["orders"])
def get_order_history(request, order_id: int):
    order = get_object_or_404(Order, id=order_id)
    history = OrderStatusHistory.objects.filter(order=order).order_by('changed_at')
    data = []
    for h in history:
        data.append({
            "from_status": h.from_status,
            "to_status": h.to_status,
            "reason": h.reason,
            "changed_by": h.changed_by_id,
            "changed_at": h.changed_at,
        })
    return JsonResponse({"success": True, "order_id": order.id, "data": data})


"""Get API Logs"""
@api.get("/api-logs", tags=["admin"])
def get_api_logs(request, limit: int = 200, endpoint: Optional[str] = None, status_code: Optional[int] = None):
    if not require_staff(request):
        return JsonResponse({"success": False, "message": "Forbidden"}, status=403)
    
    qs = APILog.objects.all()
    if endpoint:
        qs = qs.filter(endpoint__icontains=endpoint)
    if status_code:
        qs = qs.filter(status_code=status_code)
    qs = qs[:limit]
    
    logs = []
    for log in qs:
        logs.append({
            "id": log.id,
            "endpoint": log.endpoint,
            "method": log.method,
            "status_code": log.status_code,
            "response_time_ms": log.response_time_ms,
            "user_id": log.user_id,
            "error_message": log.error_message,
            "request_body": log.request_body,
            "response_body": log.response_body[:500] if log.response_body else None,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat(),
        })
    
    return JsonResponse({"success": True, "data": logs})


"""Paginated and Filterable Orders"""

@api.get("/orders/list", tags=["orders"])
@log_api_call
def list_orders(request,
                page: int = 1,
                page_size: int = 20,
                status: Optional[str] = None,
                clerk_id: Optional[str] = None,
                date_from: Optional[str] = None,
                date_to: Optional[str] = None,
                min_total: Optional[float] = None,
                max_total: Optional[float] = None):
    """
    Return orders with server-side pagination and common filters.
    """
    # Only include orders with a successful payment by default
    qs = (
        Order.objects
        .select_related("user")
        .prefetch_related("items__product")
        .filter(payments__payment_status='success')
        .order_by("-created_at")
        .distinct()
    )

    # Optional status filter still applies on top of paid constraint
    if status:
        qs = qs.filter(status=status)

    if clerk_id:
        qs = qs.filter(user__clerkId=clerk_id)

    if date_from:
        try:
            start_dt = datetime.fromisoformat(date_from)
            qs = qs.filter(created_at__gte=start_dt)
        except Exception:
            pass

    if date_to:
        try:
            end_dt = datetime.fromisoformat(date_to)
            qs = qs.filter(created_at__lte=end_dt)
        except Exception:
            pass

    if min_total is not None:
        qs = qs.filter(total_amount__gte=min_total)

    if max_total is not None:
        qs = qs.filter(total_amount__lte=max_total)

    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    items = []
    for order in page_obj.object_list:
        order_items = []
        for item in order.items.all():
            order_items.append({
                "order_item_id": item.id,
                "product_id": item.product.id,
                "product_name": item.product.product_name,
                "quantity": item.quantity,
                "price": float(item.price),
                "total": float(item.total_price()),
            })

        items.append({
            "id": order.id,
            "user_id": order.user.id,
            "total_amount": float(order.total_amount) if order.total_amount else float(order.get_total_amount()),
            "status": order.status,
            "order_date": order.order_date,
            "order_time": order.order_time,
            "created_at": order.created_at,
            "shipping_address": order.shipping_address,
            "billing_address": order.billing_address,
            "items": order_items,
        })

    return JsonResponse({
        "success": True,
        "page": page_obj.number,
        "page_size": page_obj.paginator.per_page,
        "total_pages": page_obj.paginator.num_pages,
        "total_items": page_obj.paginator.count,
        "data": items,
    })


"""Basic Orders Stats (last 30 days and totals)"""

@api.get("/orders/stats", tags=["orders"])
@log_api_call
def orders_stats(request):
    from datetime import timedelta
    now = timezone.now()
    start = now - timedelta(days=30)

    qs = Order.objects.filter(created_at__gte=start)
    total_revenue = 0.0
    status_counts = {}
    daily = {}
    for st, _ in Order.STATUS_CHOICES:
        status_counts[st] = 0

    for o in qs:
        amt = float(o.total_amount or o.get_total_amount())
        total_revenue += amt
        status_counts[o.status] = status_counts.get(o.status, 0) + 1
        day = o.created_at.date().isoformat()
        daily[day] = daily.get(day, 0.0) + amt

    series = sorted([{ 'date': d, 'revenue': v } for d, v in daily.items()], key=lambda x: x['date'])

    return JsonResponse({
        'success': True,
        'data': {
            'total_revenue_30d': round(total_revenue, 2),
            'status_counts_30d': status_counts,
            'daily_revenue_30d': series,
        }
    })


"""Set Order Status with reason (admin)"""

@api.post("/orders/{order_id}/status", tags=["orders"])
def set_order_status(request, order_id: int, payload: OrderStatusUpdateSchema):
    if not require_staff(request):
        return JsonResponse({"success": False, "message": "Forbidden"}, status=403)
    order = get_object_or_404(Order, id=order_id)

    allowed = [s[0] for s in Order.STATUS_CHOICES]
    if payload.status not in allowed:
        return JsonResponse({"success": False, "message": "Invalid status"}, status=400)

    previous_status = order.status
    order.status = payload.status
    order.save()

    # Explicit history entry including reason and actor when available
    actor = None
    try:
        if getattr(request, 'user', None) and request.user.is_authenticated:
            actor = HomeChoiceUser.objects.filter(id=request.user.id).first()
    except Exception:
        actor = None

    OrderStatusHistory.objects.create(
        order=order,
        from_status=previous_status,
        to_status=payload.status,
        reason=payload.reason or '',
        changed_by=actor,
    )

    return JsonResponse({
        "success": True,
        "message": "Status updated",
        "data": {"id": order.id, "status": order.status},
    })

"""Get Order By ID"""
@api.get("/orders/{order_id}", tags=["orders"])
@log_api_call
def get_order_by_id(request, order_id: int):
    """
    Retrieve a single order by its ID.
    """
    order = get_object_or_404(Order.objects.prefetch_related("items__product"), id=order_id)
    
    items = []
    for item in order.items.all():
        items.append({
            "order_item_id": item.id,
            "product_id": item.product.id,
            "product_name": item.product.product_name,
            "quantity": item.quantity,
            "price": float(item.price),
            "total": float(item.total_price())
        })
    
    return JsonResponse({
        "success": True,
        "data": {
            "id": order.id,
            "user_id": order.user.id,
            "total_amount": float(order.total_amount) if order.total_amount else float(order.get_total_amount()),
            "status": order.status,
            "order_date": order.order_date,
            "order_time": order.order_time,
            "created_at": order.created_at,
            "items": items
        }
    })

"""Create Order (Bulk)"""

@api.post("/orders", tags=["orders"])
def create_order(request, payload: BulkOrderSchema):
    """
    Create a new order with multiple products and quantities.
    """
    try:
        # Auth guard
        if not request.user or not request.user.is_authenticated:
            return JsonResponse({"success": False, "message": "Unauthorized"}, status=401)
        user = request.user
        
        # Create the order
        order = Order.objects.create(
            user=user,
            total_amount=payload.total_amount,
            status=payload.status or 'pending',
            order_date=timezone.now().date(),
            order_time=timezone.now().time()
        )
        
        # Create order items for each cart item
        order_items = []
        for cart_item in payload.cart_items:
            product = get_object_or_404(Product, id=cart_item.product_id)
            
            order_item = OrderItem.objects.create(
                order=order,
                product=product,
                quantity=cart_item.quantity,
                price=cart_item.price
            )
            order_items.append({
                "product_id": product.id,
                "product_name": product.product_name,
                "quantity": cart_item.quantity,
                "price": float(cart_item.price),
                "total": float(order_item.total_price())
            })
        
        # Calculate total amount from items
        order.total_amount = order.get_total_amount()
        order.save()

        return JsonResponse({
            "success": True,
            "message": "Order created successfully",
            "order_id": order.id,
            "total_amount": float(order.total_amount),
            "items": order_items
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": "Failed to create order",
            "details": str(e)
        }, status=500)

"""Update Order By ID"""

@api.put("/orders/{order_id}", tags=["orders"])
def update_order(request, order_id: int, payload: OrderUpdateSchema):
    """
    Update top-level order fields (status, dates, addresses).
    """
    order = get_object_or_404(Order, id=order_id)

    if payload.status is not None:
        order.status = payload.status
    if payload.order_date is not None:
        order.order_date = payload.order_date
    if payload.order_time is not None:
        order.order_time = payload.order_time
    if payload.shipping_address is not None:
        order.shipping_address = payload.shipping_address
    if payload.billing_address is not None:
        order.billing_address = payload.billing_address

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


"""Order Item CRUD"""

@api.post("/orders/{order_id}/items", tags=["orders"])
def add_order_item(request, order_id: int, payload: OrderItemCreateSchema):
    order = get_object_or_404(Order, id=order_id)
    product = get_object_or_404(Product, id=payload.product_id)

    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=payload.quantity,
        price=payload.price,
    )

    order.total_amount = order.get_total_amount()
    order.save()

    return JsonResponse({
        "success": True,
        "message": "Item added",
        "item": {
            "id": item.id,
            "product_id": item.product.id,
            "quantity": item.quantity,
            "price": float(item.price),
            "total": float(item.total_price()),
        },
        "order_total": float(order.total_amount),
    })


@api.put("/orders/{order_id}/items/{item_id}", tags=["orders"])
def update_order_item(request, order_id: int, item_id: int, payload: OrderItemUpdateSchema):
    order = get_object_or_404(Order, id=order_id)
    item = get_object_or_404(OrderItem, id=item_id, order=order)

    if payload.quantity is not None:
        item.quantity = payload.quantity
    if payload.price is not None:
        item.price = payload.price
    item.save()

    order.total_amount = order.get_total_amount()
    order.save()

    return JsonResponse({
        "success": True,
        "message": "Item updated",
        "item": {
            "id": item.id,
            "product_id": item.product.id,
            "quantity": item.quantity,
            "price": float(item.price),
            "total": float(item.total_price()),
        },
        "order_total": float(order.total_amount),
    })


@api.delete("/orders/{order_id}/items/{item_id}", tags=["orders"])
def delete_order_item(request, order_id: int, item_id: int):
    order = get_object_or_404(Order, id=order_id)
    item = get_object_or_404(OrderItem, id=item_id, order=order)
    item.delete()

    order.total_amount = order.get_total_amount()
    order.save()

    return JsonResponse({
        "success": True,
        "message": "Item deleted",
        "order_total": float(order.total_amount),
    })


# ========== REFUNDS APIs ==========

"""Create Refund (admin-initiated)"""

@api.post("/refunds", tags=["refunds"])
def create_refund(request, payload: RefundCreateSchema):
    if not require_staff(request):
        return JsonResponse({"success": False, "message": "Forbidden"}, status=403)
    payment = get_object_or_404(Payment, id=payload.payment_id)
    order = payment.order

    # Validate refund amount doesn't exceed paid minus already processed refunds
    processed_total = payment.refunds.filter(status='processed').aggregate(total=Sum('amount'))['total'] or 0
    remaining = float(payment.amount_paid) - float(processed_total)
    if payload.amount <= 0 or payload.amount > remaining:
        return JsonResponse({
            "success": False,
            "message": "Invalid refund amount",
            "remaining_refundable": remaining,
        }, status=400)

    refund = Refund.objects.create(
        order=order,
        payment=payment,
        amount=payload.amount,
        currency=payload.currency or payment.currency,
        reason=payload.reason or '',
        status='pending',
    )

    return JsonResponse({
        "success": True,
        "message": "Refund created",
        "data": {
            "id": refund.id,
            "order_id": refund.order.id,
            "payment_id": refund.payment.id,
            "amount": float(refund.amount),
            "currency": refund.currency,
            "reason": refund.reason,
            "status": refund.status,
            "created_at": refund.created_at,
        },
    })


"""List Refunds (with optional filters)"""

@api.get("/refunds", tags=["refunds"])
def list_refunds(request, order_id: Optional[int] = None, payment_id: Optional[int] = None, status: Optional[str] = None):
    qs = Refund.objects.select_related('order', 'payment').all().order_by('-created_at')
    if order_id:
        qs = qs.filter(order_id=order_id)
    if payment_id:
        qs = qs.filter(payment_id=payment_id)
    if status:
        qs = qs.filter(status=status)

    data = []
    for r in qs:
        data.append({
            "id": r.id,
            "order_id": r.order.id,
            "payment_id": r.payment.id,
            "amount": float(r.amount),
            "currency": r.currency,
            "reason": r.reason,
            "status": r.status,
            "processed_at": r.processed_at,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        })
    return JsonResponse({"success": True, "data": data})


"""Update Refund Status (processed/failed)"""

@api.put("/refunds/{refund_id}/status", tags=["refunds"])
def update_refund_status(request, refund_id: int, status: str):
    if not require_staff(request):
        return JsonResponse({"success": False, "message": "Forbidden"}, status=403)
    if status not in ['processed', 'failed']:
        return JsonResponse({"success": False, "message": "Invalid status"}, status=400)

    refund = get_object_or_404(Refund, id=refund_id)
    refund.status = status
    if status == 'processed' and not refund.processed_at:
        refund.processed_at = timezone.now()
    refund.save()

    # If fully refunded, set order status to refunded
    payment = refund.payment
    order = refund.order
    processed_total = payment.refunds.filter(status='processed').aggregate(total=Sum('amount'))['total'] or 0
    try:
        order_total = float(order.total_amount) if order.total_amount is not None else float(order.get_total_amount())
    except Exception:
        order_total = float(processed_total) + 1  # prevent accidental transition

    if float(processed_total) >= order_total:
        order.status = 'refunded'
        order.save()

    return JsonResponse({
        "success": True,
        "message": "Refund updated",
        "refund": {
            "id": refund.id,
            "status": refund.status,
            "processed_at": refund.processed_at,
        },
        "order_status": order.status,
    })


# ========== SHIPMENTS APIs ==========

"""Create Shipment for an Order"""

@api.post("/shipments", tags=["shipments"])
def create_shipment(request, payload: ShipmentCreateSchema):
    if not require_staff(request):
        return JsonResponse({"success": False, "message": "Forbidden"}, status=403)
    order = get_object_or_404(Order, id=payload.order_id)

    shipment = Shipment.objects.create(
        order=order,
        carrier=payload.carrier or '',
        tracking_number=payload.tracking_number or '',
        status=payload.status or 'pending',
        shipped_at=payload.shipped_at,
        delivered_at=payload.delivered_at,
        notes=payload.notes or '',
    )

    for it in payload.items:
        order_item = get_object_or_404(OrderItem, id=it.order_item_id, order=order)
        ShipmentItem.objects.create(
            shipment=shipment,
            order_item=order_item,
            quantity=it.quantity,
        )

    # Only transition to processing if the order has a successful payment
    has_success_payment = Payment.objects.filter(order=order, payment_status='success').exists()
    if not has_success_payment:
        return JsonResponse({"success": False, "message": "Order is not paid"}, status=400)
    order.status = 'processing'
    order.save()

    return JsonResponse({
        "success": True,
        "message": "Shipment created",
        "data": {
            "id": shipment.id,
            "order_id": shipment.order.id,
            "status": shipment.status,
            "tracking_number": shipment.tracking_number,
            "carrier": shipment.carrier,
            "created_at": shipment.created_at,
        },
    })


"""List Shipments with filters"""

@api.get("/shipments", tags=["shipments"])
def list_shipments(request, order_id: Optional[int] = None, status: Optional[str] = None, tracking_number: Optional[str] = None):
    qs = Shipment.objects.select_related('order').all().order_by('-created_at')
    if order_id:
        qs = qs.filter(order_id=order_id)
    if status:
        qs = qs.filter(status=status)
    if tracking_number:
        qs = qs.filter(tracking_number__icontains=tracking_number)

    data = []
    for s in qs:
        data.append({
            "id": s.id,
            "order_id": s.order.id,
            "carrier": s.carrier,
            "tracking_number": s.tracking_number,
            "status": s.status,
            "shipped_at": s.shipped_at,
            "delivered_at": s.delivered_at,
            "notes": s.notes,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        })
    return JsonResponse({"success": True, "data": data})


"""Shipment detail"""

@api.get("/shipments/{shipment_id}", tags=["shipments"])
def get_shipment(request, shipment_id: int):
    s = get_object_or_404(Shipment.objects.select_related('order').prefetch_related('items__order_item__product'), id=shipment_id)
    items = []
    for si in s.items.all():
        items.append({
            "id": si.id,
            "order_item_id": si.order_item.id,
            "product_id": si.order_item.product.id,
            "product_name": si.order_item.product.product_name,
            "quantity": si.quantity,
        })
    return JsonResponse({
        "success": True,
        "data": {
            "id": s.id,
            "order_id": s.order.id,
            "carrier": s.carrier,
            "tracking_number": s.tracking_number,
            "status": s.status,
            "shipped_at": s.shipped_at,
            "delivered_at": s.delivered_at,
            "notes": s.notes,
            "items": items,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
    })


"""Update shipment fields and transition order on status"""

@api.put("/shipments/{shipment_id}", tags=["shipments"])
def update_shipment(request, shipment_id: int, payload: ShipmentUpdateSchema):
    if not require_staff(request):
        return JsonResponse({"success": False, "message": "Forbidden"}, status=403)
    s = get_object_or_404(Shipment, id=shipment_id)
    if payload.carrier is not None:
        s.carrier = payload.carrier
    if payload.tracking_number is not None:
        s.tracking_number = payload.tracking_number
    if payload.status is not None:
        s.status = payload.status
    if payload.shipped_at is not None:
        s.shipped_at = payload.shipped_at
    if payload.delivered_at is not None:
        s.delivered_at = payload.delivered_at
    if payload.notes is not None:
        s.notes = payload.notes
    s.save()

    order = s.order
    # Transition order status based on shipment status
    if s.status == 'shipped' and order.status not in ['shipped', 'delivered']:
        order.status = 'shipped'
        order.save()
    elif s.status == 'delivered':
        # If any shipment delivered, mark order delivered; could be refined to all delivered
        order.status = 'delivered'
        order.save()

    return JsonResponse({
        "success": True,
        "message": "Shipment updated",
        "data": {
            "id": s.id,
            "status": s.status,
            "tracking_number": s.tracking_number,
        },
        "order_status": order.status,
    })

"""Get Orders By User ID"""

@api.get("/orders/user/clerk/{clerk_id}", tags=["orders"])
def get_orders_by_clerk_id(request, clerk_id: str):
    """
    Retrieve all orders made by a user using their Clerk ID.
    """
    user = get_object_or_404(HomeChoiceUser, clerkId=clerk_id)
    orders = Order.objects.prefetch_related("items__product").filter(user=user)

    data = []
    for order in orders:
        items = []
        for item in order.items.all():
            items.append({
                "product_id": item.product.id,
                "product_name": item.product.product_name,
                "quantity": item.quantity,
                "price": float(item.price),
                "total": float(item.total_price())
            })
        
        data.append({
            "id": order.id,
            "total_amount": float(order.total_amount) if order.total_amount else float(order.get_total_amount()),
            "status": order.status,
            "order_date": order.order_date,
            "order_time": order.order_time,
            "created_at": order.created_at,
            "items": items
        })
    
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

@api.post("/payments/verify", tags=["payments"], auth=None)
def verify_payment(request, payload: PaymentVerifySchema):
    """
    Handle Paystack webhook and verify payment.
    This endpoint receives Paystack webhooks and updates payment status.
    """
    try:
        # Internal HMAC Auth (Option A)
        raw_body = request.body.decode("utf-8") if hasattr(request, "body") else ""
        header_ts = request.headers.get("X-Internal-Timestamp") or request.META.get("HTTP_X_INTERNAL_TIMESTAMP")
        header_sig = request.headers.get("X-Internal-Signature") or request.META.get("HTTP_X_INTERNAL_SIGNATURE")

        if not header_ts or not header_sig:
            return JsonResponse({"success": False, "message": "Unauthorized"}, status=401)

        try:
            ts = int(header_ts)
        except Exception:
            return JsonResponse({"success": False, "message": "Unauthorized"}, status=401)

        tolerance = int(config("TIMESTAMP_TOLERANCE_SECONDS", default=300))
        now = int(time.time())
        if abs(now - ts) > tolerance:
            return JsonResponse({"success": False, "message": "Unauthorized (stale request)"}, status=401)

        secret = config("INTERNAL_VERIFY_SECRET", default=None)
        if not secret:
            return JsonResponse({"success": False, "message": "Server misconfigured"}, status=500)

        message = f"{ts}.{raw_body}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, header_sig.lower()):
            return JsonResponse({"success": False, "message": "Unauthorized"}, status=401)

        # Parse Paystack payload after passing HMAC
        data_json = json.loads(raw_body) if raw_body else {}
        event = data_json.get("event")
        data = data_json.get("data") or {}
        
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
                
                # Link payment to order; keep order status unchanged here
                order = payment.order
                order.payment = payment
                order.save(update_fields=["payment", "updated_at"])
                
            else:
                payment.payment_status = 'failed'
                payment.set_paystack_response(paystack_data['data'])
        
        payment.save()

        # Webhook logging to file (no DB). Store minimal info
        try:
            from django.conf import settings
            import os
            log_dir = os.path.join(getattr(settings, 'BASE_DIR', ''), 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, 'paystack_webhooks.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    'ts': int(time.time()),
                    'event': event,
                    'reference': reference,
                    'payment_id': payment.id,
                    'status': payment.payment_status,
                }) + "\n")
        except Exception:
            pass
        
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
@log_api_call
def get_all_payments(request):
    if not require_staff(request):
        return JsonResponse({"success": False, "message": "Forbidden"}, status=403)
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
    if not require_staff(request):
        return JsonResponse({"success": False, "message": "Forbidden"}, status=403)
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
