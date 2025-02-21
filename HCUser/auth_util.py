from clerk_backend_api import Clerk
from clerk_backend_api.jwks_helpers import AuthenticateRequestOptions
import httpx

CLERK_SECRET_KEY = 'sk_test_MirhNJiANXHFXrOiSs6q2LvKRFxUBYXFNlBAL0BjPH'

clerk = Clerk(bearer_auth=CLERK_SECRET_KEY)

def authenticate_clerk_user(request: httpx.Request):
    request_state = clerk.authenticate_request(
        request,
        AuthenticateRequestOptions(
            authorized_parties=["https://homechoice-depot.vercel.app"]
        )
    )
    return request_state
