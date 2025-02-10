from django.shortcuts import render
from ninja_extra import NinjaExtraAPI, api_controller, http_get
from ninja_extra.permissions import IsAuthenticated
from .schemas import SignupSchema, ResponseSchema, LoginSchema
from .models import HomeChoiceUser
from django.contrib.auth import authenticate, logout
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_jwt.controller import TokenObtainPairController

"""NinjaExtra API FOR HomeChoice"""

api = NinjaExtraAPI()


# @api_controller("token", tags=["Auth"])
# class MyTokenController(TokenObtainPairController):
#     """Controller for obtaining and refreshing JWT tokens."""

#     pass  # Inherits obtain_token and refresh_token methods from TokenObtainPairController


# # Register the controller with the API instance
# api.register_controllers(MyTokenController)

api.register_controllers(NinjaJWTDefaultController)

"""Intrinsic Data Handling"""


@api.get("/hello", tags=["Tests"])
def hello(request, name: str = "World"):
    return {"message": f"Hello, {name}!"}


@api.get("/add", tags=["Tests"])
def add(request, a: int, b: int):
    return {"result": a + b}


"""Extrinsic Data Handling"""

"""User SignUp"""


@api.post("/signup", response=ResponseSchema, tags=["User"])
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


@api.post("/login/homechoice-user", response=ResponseSchema, tags=["User"])
def user_login(request, payload: LoginSchema):

    user = authenticate(email=payload.email, password=payload.password)

    if user is not None and not user.is_staff:
        return {
            "success": True,
            "message": "User login successful.",
            "data": {
                "email": user.email,
                "user_id": user.pk,
                "username": user.username,
            },
        }

    return {"success": False, "message": "Invalid credentials or not a common user."}


"""Admin Login"""


@api.post("/login/homechoice-admin", response=ResponseSchema, tags=["User"])
def admin_login(request, payload: LoginSchema):

    user = authenticate(email=payload.email, password=payload.password)

    if user is not None and user.is_staff:
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

@api.post("/logout", response=ResponseSchema, tags=["User"])
def user_logout(request):

    user_ = request.user

    if request.user.is_authenticated:
        logout(request)
        return {"success": True, "message": "Logout successful."}

    return {
        "success": False,
        "message": "User is not authenticated.",
        "data": {"email": user_.email, "username": user_.username},
    }
