from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Any, Optional, List, Dict


class ResponseSchema(BaseModel):
    success: bool
    message: str
    data: Any = None

class LoginSchema(BaseModel):
    email: str
    password: Optional[str] = Field(None, description="Required for OAuth users, ignored for traditional users")
    
class SignupSchema(BaseModel):
    email: str
    username: str
    password: Optional[str] = Field(None, description="Required for OAuth users, ignored for traditional users")
    clerkId: Optional[str] = Field(None, description="Required for OAuth users, ignored for traditional users")
    is_staff: bool = False
    is_superuser: bool = False


class StaffUpdateSchema(BaseModel):
    clerk_id: str
    is_staff: bool


class ContactNumberSchema(BaseModel):
    contact_number: str

    @field_validator("contact_number")
    @classmethod
    def validate_contact_number(cls, value: str) -> str:
        if not value.startswith("+254") or len(value) != 13 or not value[1:].isdigit():
            raise ValueError("Number must start with +254 and have 9 additional digits.")
        return value
