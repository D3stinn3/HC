from django.shortcuts import render
from ninja_extra import NinjaExtraAPI, api_controller, http_get
from ninja_extra.permissions import IsAuthenticated


"""NinjaExtra API FOR HomeChoice"""

api = NinjaExtraAPI()

"""Intrinsic Data Handling"""

@api.get("/hello", tags=['HCUser'])
def hello(request, name: str = "World"):
    return {"message": f"Hello, {name}!"}

@api.get("/add", tags=['HCUser'])
def add(request, a: int, b: int):
    return {"result": a + b}

"""Extrinsic Data Handling"""





