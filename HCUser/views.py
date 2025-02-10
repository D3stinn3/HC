from django.shortcuts import render
from ninja_extra import NinjaExtraAPI, api_controller, http_get
from ninja_extra.permissions import IsAuthenticated


# Create your views here.
api = NinjaExtraAPI()

@api.get("/hello", tags=['Basic'])
def hello(request, name: str = "World"):
    return {"message": f"Hello, {name}!"}

@api.get("/add", tags=['Basic'])
def add(request, a: int, b: int):
    return {"result": a + b}


