from .models import APILog
from django.utils import timezone
import json
import time
from functools import wraps

def log_api_call(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        start_time = time.time()
        endpoint = request.path
        method = request.method
        user_id = None
        try:
            if hasattr(request, 'user') and request.user and hasattr(request.user, 'id'):
                user_id = request.user.id
        except:
            pass
        
        ip_address = request.META.get('REMOTE_ADDR', '') or request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
        
        request_body = None
        try:
            if hasattr(request, 'body') and request.body:
                try:
                    request_body = request.body.decode('utf-8')[:1000]  # Limit size
                except:
                    request_body = str(request.body)[:1000]
        except:
            pass
        
        status_code = None
        response_body = None
        error_message = None
        
        try:
            response = func(request, *args, **kwargs)
            if hasattr(response, 'status_code'):
                status_code = response.status_code
            if hasattr(response, 'content'):
                try:
                    response_body = response.content.decode('utf-8')[:2000]  # Limit size
                except:
                    response_body = str(response.content)[:2000]
            response_time_ms = int((time.time() - start_time) * 1000)
            
            APILog.objects.create(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                user_id=user_id,
                request_body=request_body,
                response_body=response_body,
                ip_address=ip_address,
            )
            
            return response
        except Exception as e:
            error_message = str(e)[:500]
            response_time_ms = int((time.time() - start_time) * 1000)
            status_code = 500
            
            APILog.objects.create(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                user_id=user_id,
                error_message=error_message,
                request_body=request_body,
                ip_address=ip_address,
            )
            raise
            
    return wrapper

