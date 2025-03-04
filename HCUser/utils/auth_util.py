from clerk_backend_api import Clerk
from clerk_backend_api.jwks_helpers import AuthenticateRequestOptions
import httpx
from django.conf import settings
import requests
import jwt
from jwt import PyJWTError
from functools import wraps
from django.http import JsonResponse
from clerk_backend_api import Clerk
import logging
from django.conf import settings
from decouple import config

CLERK_SECRET_KEY = config("CLERK_SECRET_KEY")
CLERK_FRONTEND_URL = config("CLERK_FRONTEND_URL")

clerk = Clerk(bearer_auth=CLERK_SECRET_KEY)

def authenticate_clerk_user(request: httpx.Request):
    request_state = clerk.authenticate_request(
        request,
        AuthenticateRequestOptions(
            authorized_parties=[CLERK_FRONTEND_URL]
        )
    )
    return request_state



# Decorator for Clerk authentication using `authenticate_clerk_user`
def clerk_authenticated(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            # Convert Django request to httpx.Request
            httpx_request = httpx.Request(
                method=request.method,
                url=request.build_absolute_uri(),
                headers=request.headers,
            )

            # Authenticate request with Clerk SDK
            request_state = clerk.authenticate_request(
                httpx_request,
                AuthenticateRequestOptions(
                    authorized_parties=[CLERK_FRONTEND_URL]
                ),
            )

            # Check if the user is signed in
            if not request_state.is_signed_in:
                return JsonResponse(
                    {"error": "Authentication failed", "reason": request_state.reason},
                    status=401,
                )

            # Retrieve user details from Clerk
            user_id = request_state.payload.get("sub")  # Extract user ID from token
            user_details = clerk.users.get(user_id) if user_id else None

            if not user_details:
                return JsonResponse({"error": "User details not found"}, status=401)

            # Attach user details to the request for further use
            request.user_details = user_details

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=401)

        return view_func(request, *args, **kwargs)

    return wrapper
