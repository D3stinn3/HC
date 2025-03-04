import httpx
from ninja_extra.permissions import BasePermission
from clerk_backend_api import Clerk
from clerk_backend_api.jwks_helpers import AuthenticateRequestOptions
from decouple import config

CLERK_SECRET_KEY = config("CLERK_SECRET_KEY")
CLERK_FRONTEND_URL = config("CLERK_FRONTEND_URL")

clerk = Clerk(bearer_auth=CLERK_SECRET_KEY)

# **Custom Clerk Authentication Permission**
class ClerkAuthenticationPermission(BasePermission):
    def has_permission(self, request, view):
        try:
            # Convert Django request to httpx.Request
            httpx_request = httpx.Request(
                method=request.method,
                url=request.build_absolute_uri(),
                headers=request.headers,
            )

            # Authenticate request with Clerk
            request_state = clerk.authenticate_request(
                httpx_request,
                AuthenticateRequestOptions(
                    authorized_parties=[CLERK_FRONTEND_URL]
                ),
            )

            if request_state.is_signed_in:
                # Attach user details to request
                request.user = request_state.payload
                return True
        except Exception as e:
            return False

        return False