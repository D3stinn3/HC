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
from .auth_util import authenticate_clerk_user
from django.contrib.auth import get_user_model
from django.core.cache import caches


"""NinjaExtra API FOR HomeChoice"""

api = NinjaExtraAPI()

api.register_controllers(NinjaJWTDefaultController)

"""Redis Cache"""

# Use Django Redis cache
csrf_cache = caches["default"]

"""Initialize API"""
api = NinjaExtraAPI()

# Use Django Redis cache
csrf_cache = caches["default"]

"""Intrinsic Data Handling"""
# @api.get("/get_csrf_token")
# def get_csrf_token(request):
#     return {'csrf_token': get_token(request)}

@api.get("/hello", tags=["tests"])
def hello(request, name: str = "World"):
    return {"message": f"Hello, {name}!"}


@api.get("/add", tags=["tests"])
def add(request, a: int, b: int):
    return {"result": a + b}


"""Extrinsic Data Handling"""


""" CSRF Token Management """

@api.get("/get_csrf_token", response=ResponseSchema, tags=["csrf"])
def get_csrf_token_api(request, user_id: str):
    """
    Retrieves CSRF token from Redis or generates a new one.
    """
    csrf_token = csrf_cache.get(f"csrf_token:{user_id}")

    if not csrf_token:
        csrf_token = get_token(request)  # Generate new CSRF token
        csrf_cache.set(f"csrf_token:{user_id}", csrf_token, timeout=None)  # Store indefinitely

    return {
        "success": True,
        "message": "CSRF token retrieved successfully",
        "data": {"csrf_token": csrf_token}
    }



@api.post("/store_csrf_token", response=ResponseSchema, tags=["csrf"])
def store_csrf_token(request, user_id: str):
    """
    Stores CSRF token in Redis for the given user.
    """
    csrf_token = get_token(request)
    csrf_cache.set(f"csrf_token:{user_id}", csrf_token, timeout=None)

    return {"success": True, "message": "CSRF token stored successfully", "data" : {"csrf_token": csrf_token}}


@api.post("/delete_csrf_token", response=ResponseSchema, tags=["csrf"])
def delete_csrf_token(request, user_id: str):
    """
    Deletes CSRF token from Redis for the given user.
    """
    csrf_cache.delete(f"csrf_token:{user_id}")

    return {"success": True, "message": "CSRF token deleted successfully"}


"""User SignUp"""


# @api.post("/signup", response=ResponseSchema, tags=["user"])
# def signup(request, payload: SignupSchema):

#     if HomeChoiceUser.objects.filter(email=payload.email).exists():
#         return {"success": False, "message": "Email already registered."}

#     if HomeChoiceUser.objects.filter(username=payload.username).exists():
#         return {"success": False, "message": "Username already taken."}

#     user = HomeChoiceUser.objects.create_user(
#         email=payload.email,
#         username=payload.username,
#         password=payload.password,
#         is_staff=payload.is_staff,
#         is_superuser=payload.is_superuser,
#         clerkId=payload.clerkId
#     )

#     return {
#         "success": True,
#         "message": "User registered successfully.",
#         "data": {"email": user.email},
#     }


# @api.post("/signup", response=ResponseSchema, tags=["user"])
# def signup(request, payload: SignupSchema):

#     if HomeChoiceUser.objects.filter(email=payload.email).exists():
#         return {"success": False, "message": "Email already registered."}

#     if HomeChoiceUser.objects.filter(username=payload.username).exists():
#         return {"success": False, "message": "Username already taken."}

#     # Use Clerk ID as the password for OAuth users
#     if payload.clerkId:
#         generated_password = payload.clerkId
#     else:
#         generated_password = payload.password  # Use provided password for traditional users

#     # Create the user with the generated password
#     user = HomeChoiceUser.objects.create_user(
#         email=payload.email,
#         username=payload.username,
#         password=generated_password,  # Either Clerk ID or user-provided password
#         is_staff=payload.is_staff,
#         is_superuser=payload.is_superuser,
#         clerkId=payload.clerkId
#     )

#     return {
#         "success": True,
#         "message": "User registered successfully.",
#         "data": {"email": user.email},
#     }

@api.post("/signup", response=ResponseSchema, tags=["user"])
def signup(request, payload: SignupSchema):
    """
    Handles user signup and stores CSRF token in Redis.
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

    # Store CSRF token in Redis
    csrf_token = get_token(request)
    csrf_cache.set(f"csrf_token:{user.pk}", csrf_token, timeout=None)

    return {
        "success": True,
        "message": "User registered successfully.",
        "data": {"email": user.email, "csrf_token": csrf_token},
    }


"""User Login"""


# @api.post("/login/homechoice-user", response=ResponseSchema, tags=["user"])
# def user_login(request, payload: LoginSchema):
#     user = authenticate(request, username=payload.email, password=payload.password)  # Use authenticate

#     if user is not None and not user.is_staff:
#         login(request, user)  # Log in the authenticated user
#         return {
#             "success": True,
#             "message": "User login successful.",
#             "data": {
#                 "email": user.email,
#                 "user_id": user.pk,
#                 "username": user.username,
#             },
#         }

#     return {"success": False, "message": "Invalid credentials or not a common user."}

# @api.post("/login/homechoice-user", response=ResponseSchema, tags=["user"])
# def user_login(request, payload: LoginSchema):
#     """
#     Logs in users:
#     - Traditional users authenticate normally.
#     - OAuth users use Clerk ID as password.
#     """

#     # Check if user exists
#     user = HomeChoiceUser.objects.filter(email=payload.email).first()

#     if not user:
#         return {"success": False, "message": "User not found. Please sign up first."}

#     # Use Clerk ID as the password for OAuth users
#     password_ = user.clerkId if user.clerkId else payload.password

#     user = authenticate(request, username=payload.email, password=password_)

#     if user is not None and not user.is_staff:
#         login(request, user)
#         return {
#             "success": True,
#             "message": "User login successful.",
#             "data": {
#                 "email": user.email,
#                 "user_id": user.pk,
#                 "username": user.username,
#             },
#         }

#     return {"success": False, "message": "Invalid credentials or not a common user."}

@api.post("/login/homechoice-user", response=ResponseSchema, tags=["user"])
def user_login(request, payload: LoginSchema):
    """
    Logs in users and retrieves or stores CSRF token from Redis.
    """

    user = HomeChoiceUser.objects.filter(email=payload.email).first()
    if not user:
        return {"success": False, "message": "User not found. Please sign up first."}

    password_ = user.clerkId if user.clerkId else payload.password
    user = authenticate(request, username=payload.email, password=password_)

    if user is not None and not user.is_staff:
        login(request, user)

        # Get CSRF Token from Redis or Generate a New One
        csrf_token = csrf_cache.get(f"csrf_token:{user.pk}")
        if not csrf_token:
            csrf_token = get_token(request)
            csrf_cache.set(f"csrf_token:{user.pk}", csrf_token, timeout=None)

        return {
            "success": True,
            "message": "User login successful.",
            "data": {
                "email": user.email,
                "user_id": user.pk,
                "username": user.username,
                "csrf_token": csrf_token,
            },
        }

    return {"success": False, "message": "Invalid credentials or not a common user."}




"""Admin Login"""


# @api.post("/login/homechoice-admin", response=ResponseSchema, tags=["user"])
# def admin_login(request, payload: LoginSchema):
#     user = authenticate(request, username=payload.email, password=payload.password)  # Use authenticate

#     if user is not None and user.is_staff:
#         login(request, user)  # Log in the authenticated admin
#         return {
#             "success": True,
#             "message": "Admin login successful.",
#             "data": {
#                 "email": user.email,
#                 "user_id": user.pk,
#                 "username": user.username,
#             },
#         }

#     return {"success": False, "message": "Invalid credentials or not an admin."}

# @api.post("/login/homechoice-admin", response=ResponseSchema, tags=["user"])
# def admin_login(request, payload: LoginSchema):
#     """
#     Logs in admins:
#     - Traditional admin users authenticate normally.
#     - OAuth admins use Clerk ID as password.
#     """

#     # Check if user exists
#     user = HomeChoiceUser.objects.filter(email=payload.email).first()

#     if not user:
#         return {"success": False, "message": "User not found. Please sign up first."}

#     # Use Clerk ID as the password for OAuth admins
#     password_ = user.clerkId if user.clerkId else payload.password

#     user = authenticate(request, username=payload.email, password=password_)

#     if user is not None and user.is_staff:
#         login(request, user)
#         return {
#             "success": True,
#             "message": "Admin login successful.",
#             "data": {
#                 "email": user.email,
#                 "user_id": user.pk,
#                 "username": user.username,
#             },
#         }

#     return {"success": False, "message": "Invalid credentials or not an admin."}

@api.post("/login/homechoice-admin", response=ResponseSchema, tags=["user"])
def admin_login(request, payload: LoginSchema):
    """
    Logs in admins:
    - Traditional admin users authenticate normally.
    - OAuth admins use Clerk ID as password.
    """

    # Check if admin user exists
    user = HomeChoiceUser.objects.filter(email=payload.email, is_staff=True).first()

    if not user:
        return {"success": False, "message": "Admin not found. Please check credentials."}

    # Use Clerk ID as the password for OAuth admins
    password_ = user.clerkId if user.clerkId else payload.password

    user = authenticate(request, username=payload.email, password=password_)

    if user is not None and user.is_staff:
        login(request, user)

        # Get CSRF Token from Redis or Generate a New One
        csrf_token = csrf_cache.get(f"csrf_token:{user.pk}")
        if not csrf_token:
            csrf_token = get_token(request)
            csrf_cache.set(f"csrf_token:{user.pk}", csrf_token, timeout=None)

        return {
            "success": True,
            "message": "Admin login successful.",
            "data": {
                "email": user.email,
                "user_id": user.pk,
                "username": user.username,
                "csrf_token": csrf_token,  # Return CSRF token for use in requests
            },
        }

    return {"success": False, "message": "Invalid credentials or not an admin."}



"""User Logout"""

# @api.post("/logout", response=ResponseSchema, tags=["user"])
# def user_logout(request):

#     user_ = request.user

#     if user_.is_authenticated:
#         logout(request)
#         return {"success": True, "message": "Logout successful."}

#     return {
#         "success": False,
#         "message": "User is not authenticated.",
#         "data": {"email": user_.email, "username": user_.username},
#     }

@api.post("/logout", response=ResponseSchema, tags=["user"])
def user_logout(request):
    """
    Logs out the user and deletes the CSRF token from Redis.
    """
    user_ = request.user

    if user_.is_authenticated:
        logout(request)
        csrf_cache.delete(f"csrf_token:{user_.pk}")  # Delete CSRF token

        return {"success": True, "message": "Logout successful. CSRF token removed."}

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
