from django.shortcuts import render
from ninja_extra import NinjaExtraAPI, api_controller, http_get
from ninja_extra.permissions import IsAuthenticated
from .schemas import SignupSchema, ResponseSchema, LoginSchema
from .models import HomeChoiceUser
from django.contrib.auth import authenticate, logout, login
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_jwt.controller import TokenObtainPairController
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404


"""NinjaExtra API FOR HomeChoice"""

api = NinjaExtraAPI()

api.register_controllers(NinjaJWTDefaultController)

"""Intrinsic Data Handling"""


@api.get("/hello", tags=["tests"])
def hello(request, name: str = "World"):
    return {"message": f"Hello, {name}!"}


@api.get("/add", tags=["tests"])
def add(request, a: int, b: int):
    return {"result": a + b}


"""Extrinsic Data Handling"""
@api.get("/get_csrf_token")
def get_csrf_token(request):
    return {'csrf_token': get_token(request)}

"""User SignUp"""


@api.post("/signup", response=ResponseSchema, tags=["user"])
def signup(request, payload: SignupSchema):

    if HomeChoiceUser.objects.filter(email=payload.email).exists():
        return {"success": False, "message": "Email already registered."}

    if HomeChoiceUser.objects.filter(username=payload.username).exists():
        return {"success": False, "message": "Username already taken."}

    user = HomeChoiceUser.objects.create_user(
        email=payload.email,
        username=payload.username,
        password=payload.password,
        is_staff=payload.is_staff,
        is_superuser=payload.is_superuser,
    )

    return {
        "success": True,
        "message": "User registered successfully.",
        "data": {"email": user.email},
    }


"""User Login"""


@api.post("/login/homechoice-user", response=ResponseSchema, tags=["user"])
def user_login(request, payload: LoginSchema):
    """Allow both password-based and OAuth-based logins using clerkId."""
    
    # Try authenticating with email & password (traditional login)
    user = authenticate(request, username=payload.email, password=payload.password)

    if user is not None and not user.is_staff:
        login(request, user)
        return {
            "success": True,
            "message": "User login successful.",
            "data": {
                "email": user.email,
                "user_id": user.pk,
                "username": user.username,
                "clerkId": user.clerkId,  # Include clerkId in response
            },
        }

    # **OAuth users: Check if user exists and has a clerkId**
    try:
        user = HomeChoiceUser.objects.get(email=payload.email)
        
        if user.clerkId:  # ✅ OAuth user (clerkId is present)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')  # Manually log in
            return {
                "success": True,
                "message": "OAuth user login successful.",
                "data": {
                    "email": user.email,
                    "user_id": user.pk,
                    "username": user.username,
                    "clerkId": user.clerkId,  # Include clerkId in response
                },
            }

        # If user exists but has no clerkId, reject login
        return {"success": False, "message": "Password required for non-OAuth users."}

    except HomeChoiceUser.DoesNotExist:
        return {"success": False, "message": "User not found. Please sign up first."}




"""Admin Login"""


@api.post("/login/homechoice-admin", response=ResponseSchema, tags=["user"])
def admin_login(request, payload: LoginSchema):
    user = authenticate(request, username=payload.email, password=payload.password)  # Use authenticate

    if user is not None and user.is_staff:
        login(request, user)  # Log in the authenticated admin
        return {
            "success": True,
            "message": "Admin login successful.",
            "data": {
                "email": user.email,
                "user_id": user.pk,
                "username": user.username,
            },
        }

    return {"success": False, "message": "Invalid credentials or not an admin."}


"""User Logout"""

@api.post("/logout", response=ResponseSchema, tags=["user"])
def user_logout(request):
    """Handles logout for both OAuth (Clerk) users and traditional Django users."""

    user_ = request.user

    # Check if the user is authenticated
    if request.user.is_authenticated:
        # If the user has a Clerk ID, they should be logged out from Clerk separately
        if hasattr(user_, "clerkId") and user_.clerkId:
            return {
                "success": True,
                "message": "OAuth user logout detected. Logout via Clerk is required.",
                "data": {
                    "email": user_.email,
                    "username": user_.username,
                    "clerkId": user_.clerkId,
                },
            }

        # Normal Django session-based logout
        logout(request)
        return {"success": True, "message": "Logout successful."}

    return {
        "success": False,
        "message": "User is not authenticated.",
    }

"""Delete User"""

@api.delete("/delete_user", response=ResponseSchema, tags=["user"])
def delete_user(request, email: str):
    if not request.user.is_authenticated:
        return {"success": False, "message": "Authentication required."}

    if email and request.user.is_staff:
        # Admin deleting another user
        user = get_object_or_404(HomeChoiceUser, email=email)
    else:
        # Normal user deleting their own account
        user = request.user

    user.delete()
    return {"success": True, "message": "User deleted successfully."}
