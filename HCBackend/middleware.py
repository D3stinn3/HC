import requests
from django.conf import settings
from django.http import JsonResponse

class ClerkTokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

            # Validate the token with Clerk's API
            clerk_api_url = "https://api.clerk.dev/v1/tokens/verify"
            response = requests.post(
                clerk_api_url,
                headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
                json={"token": token},
            )
            if response.status_code != 200:
                return JsonResponse({"error": "Invalid token"}, status=401)

        return self.get_response(request)
