from pydantic import BaseModel, EmailStr, Field
from typing import Any, Optional, List, Dict


class ResponseSchema(BaseModel):
    success: bool
    message: str
    data: Any = None

class LoginSchema(BaseModel):
    email: str
    password: str
    
class SignupSchema(BaseModel):
    email: str
    username: str
    password: Optional[str] = Field(None, description="Required for OAuth users, ignored for traditional users")
    clerkId: Optional[str] = Field(None, description="Required for OAuth users, ignored for traditional users")
    is_staff: bool = False
    is_superuser: bool = False

