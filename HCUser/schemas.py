from pydantic import BaseModel
from typing import Any, Optional, List, Dict


class ResponseSchema(BaseModel):
    success: bool
    message: str
    data: Any = None

class SignupSchema(BaseModel):
    email: str
    username: str
    password: str
    is_staff: bool = False
    is_superuser: bool = False
    
class LoginSchema(BaseModel):
    email: str
    password: str
