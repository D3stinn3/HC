from django.shortcuts import render
from ninja_extra import NinjaExtraAPI, api_controller, http_get
from ninja_extra.permissions import IsAuthenticated
from .schemas import SignupSchema, ResponseSchema, LoginSchema, StaffUpdateSchema
from .models import HomeChoiceUser
from django.contrib.auth import authenticate, logout, login
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_jwt.controller import TokenObtainPairController
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from ninja_jwt.authentication import JWTAuth
from HCUser.utils.permission_auth_util import ClerkAuthenticationPermission
from HCUser.utils.auth_util import clerk_authenticated
from decouple import config

"""NinjaExtra API FOR HomeChoice"""

"""Initialize API"""

api = NinjaExtraAPI()

api.register_controllers(NinjaJWTDefaultController)

"""Redis Cache"""

# Use Django Redis cache
csrf_cache = caches["default"]


"""Intrinsic Data Handling"""

@api.get("/hello", tags=["tests"])
def hello(request, name: str = "World"):
    return {"message": f"Hello, {name}!"}


@api.get("/add", tags=["tests"])
def add(request, a: int, b: int):
    return {"result": a + b}


"""Extrinsic Data Handling"""


""" CSRF Token Management """

@api.get("/get_csrf_token", response=ResponseSchema, tags=["csrf"])
@ensure_csrf_cookie
def get_csrf_token_api(request, email: str):
    """
    Retrieves CSRF token from Redis using user.email or generates a new one.
    """
    csrf_token = csrf_cache.get(f"csrf_token:{email}")

    if not csrf_token:
        csrf_token = get_token(request)  # Generate new CSRF token
        csrf_cache.set(f"csrf_token:{email}", csrf_token, timeout=None)  # Store indefinitely

    response_data = {
        "success": True,
        "message": "CSRF token retrieved successfully",
        "data": {"csrf_token": csrf_token}
    }

    return JsonResponse(response_data)


@api.post("/store_csrf_token", response=ResponseSchema, tags=["csrf"])
def store_csrf_token(request, email: str):
    """
    Stores CSRF token in Redis for the given user email.
    """
    csrf_token = get_token(request)
    csrf_cache.set(f"csrf_token:{email}", csrf_token, timeout=None)

    return {"success": True, "message": "CSRF token stored successfully", "data": {"csrf_token": csrf_token}}


@api.post("/delete_csrf_token", response=ResponseSchema, tags=["csrf"])
def delete_csrf_token(request, email: str):
    """
    Deletes CSRF token from Redis for the given user email.
    """
    csrf_cache.delete(f"csrf_token:{email}")

    return {"success": True, "message": "CSRF token deleted successfully"}



"""User SignUp"""

@api.post("/signup", response=ResponseSchema, tags=["user"])
def signup(request, payload: SignupSchema):
    """
    Handles user signup without storing CSRF token.
    """
    if HomeChoiceUser.objects.filter(email=payload.email).exists():
        return {"success": False, "message": "Email already registered."}

    if HomeChoiceUser.objects.filter(username=payload.username).exists():
        return {"success": False, "message": "Username already taken."}

    generated_password = payload.clerkId if payload.clerkId else payload.password

    user = HomeChoiceUser.objects.create_user(
        email=payload.email,
        username=payload.username,
        password=generated_password,
        is_staff=payload.is_staff,
        is_superuser=payload.is_superuser,
        clerkId=payload.clerkId
    )

    return JsonResponse({
        "success": True,
        "message": "User registered successfully.",
        "data": {"email": user.email},
    })



"""User Login"""

@api.post("/login/homechoice-user", response=ResponseSchema, tags=["user"], auth=JWTAuth())
@ensure_csrf_cookie
def user_login(request, payload: LoginSchema):
    """
    Logs in users and retrieves or stores CSRF token.
    """
    user = HomeChoiceUser.objects.filter(email=payload.email).first()
    if not user:
        return JsonResponse({"success": False, "message": "User not found. Please sign up first."})

    password_ = user.clerkId if user.clerkId else payload.password
    user = authenticate(request, username=payload.email, password=password_)

    if user is not None and not user.is_staff:
        login(request, user)

        # Get CSRF Token from Redis or Generate a New One using user.email
        csrf_token = csrf_cache.get(f"csrf_token:{user.email}")
        if not csrf_token:
            csrf_token = get_token(request)
            csrf_cache.set(f"csrf_token:{user.email}", csrf_token, timeout=None)

        return JsonResponse({
            "success": True,
            "message": "User login successful.",
            "data": {
                "email": user.email,
                "user_id": user.pk,
                "username": user.username,
                "csrf_token": csrf_token,
            },
        })

    return JsonResponse({"success": False, "message": "Invalid credentials or not a common user."})




"""Admin Login"""

@api.post("/login/homechoice-admin", response=ResponseSchema, tags=["user"], auth=JWTAuth())
@ensure_csrf_cookie
def admin_login(request, payload: LoginSchema):
    """
    Logs in admins and retrieves or stores CSRF token.
    """
    user = HomeChoiceUser.objects.filter(email=payload.email, is_staff=True).first()

    if not user:
        return JsonResponse({"success": False, "message": "Admin not found. Please check credentials."}, status=404)

    password_ = user.clerkId if user.clerkId else payload.password
    user = authenticate(request, username=payload.email, password=password_)

    if user is not None and user.is_staff:
        login(request, user)

        # Get CSRF Token from Redis or Generate a New One using user.email
        csrf_token = csrf_cache.get(f"csrf_token:{user.email}")
        if not csrf_token:
            csrf_token = get_token(request)
            csrf_cache.set(f"csrf_token:{user.email}", csrf_token, timeout=None)

        return JsonResponse({
            "success": True,
            "message": "Admin login successful.",
            "data": {
                "email": user.email,
                "user_id": user.pk,
                "username": user.username,
                "csrf_token": csrf_token,
            },
        })

    return JsonResponse({"success": False, "message": "Invalid credentials or not an admin."}, status=401)



"""User Logout"""

@api.post("/logout", response=ResponseSchema, tags=["user"], auth=JWTAuth())
@ensure_csrf_cookie
def user_logout(request):
    """
    Logs out the user and deletes the CSRF token.
    """
    user_ = request.user

    if user_.is_authenticated:
        logout(request)
        csrf_cache.delete(f"csrf_token:{user_.email}")  # Delete CSRF token using email

        return JsonResponse({"success": True, "message": "Logout successful. CSRF token removed."})

    return JsonResponse({"success": False, "message": "User is not authenticated."}, status=401)


"""Admin role sync (from Clerk webhook via admin app)"""

@api.post("/set_staff", response=ResponseSchema, tags=["user"], auth=None)
def set_staff(request, payload: StaffUpdateSchema):
    """
    Sets is_staff for a user identified by Clerk ID. Requires INTERNAL_ADMIN_SECRET header.
    """
    expected_secret = config("INTERNAL_ADMIN_SECRET", default="")
    provided = request.headers.get("X-Admin-Secret") or request.META.get("HTTP_X_ADMIN_SECRET", "")
    if not expected_secret or provided != expected_secret:
        return JsonResponse({"success": False, "message": "Unauthorized"}, status=403)

    user = HomeChoiceUser.objects.filter(clerkId=payload.clerk_id).first()
    if not user:
        return JsonResponse({"success": False, "message": "User not found"}, status=404)

    user.is_staff = payload.is_staff
    user.save(update_fields=["is_staff"])

    return JsonResponse({
        "success": True,
        "message": "Staff flag updated",
        "data": {"email": user.email, "is_staff": user.is_staff}
    })


"""Check if user is staff (by Clerk ID)"""

@api.get("/check_staff/{clerk_id}", response=ResponseSchema, tags=["user"], auth=None)
def check_staff(request, clerk_id: str):
    """
    Returns is_staff status for a user by Clerk ID. No auth required (public check).
    """
    user = HomeChoiceUser.objects.filter(clerkId=clerk_id).first()
    if not user:
        return JsonResponse({"success": False, "message": "User not found", "data": {"is_staff": False}}, status=404)

    return JsonResponse({
        "success": True,
        "message": "Staff status retrieved",
        "data": {"is_staff": user.is_staff, "email": user.email}
    })



"""Delete User"""

@api.delete("/delete_user", response=ResponseSchema, tags=["user"], auth=JWTAuth())
@ensure_csrf_cookie
def delete_user(request, clerk_id: str):
    """
    Deletes a user and removes their CSRF token from Redis using user.clerkId.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "message": "Authentication required."}, status=401)

    if clerk_id and request.user.is_staff:
        # Admin deleting another user
        user = get_object_or_404(HomeChoiceUser, clerkId=clerk_id)
    else:
        # Normal user deleting their own account
        user = request.user

    # Remove CSRF token from Redis using user.clerkId
    csrf_cache.delete(f"csrf_token:{user.clerkId}")

    user.delete()
    return JsonResponse({"success": True, "message": "User deleted successfully."})
