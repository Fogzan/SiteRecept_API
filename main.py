from fastapi import FastAPI, HTTPException, status
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from pydantic import BaseModel
import random
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
load_dotenv()
client = MongoClient(os.getenv('MONGODB_URI'))

db = client['test_db_recipes']
collection_recipes = db['recipes']
collection_users = db['users']

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешенные домены
    allow_credentials=True,
    allow_methods=["*"],  # Разрешенные HTTP-методы
    allow_headers=["*"],  # Разрешенные заголовки
)

@app.get("/")
async def main():
    return {"message": "hello world!"}

@app.get("/get-all-recipes")
async def getAllRecipes():
    result_find = collection_recipes.find({}, {"_id":0})
    result = []
    for item in result_find:
        result.append(item)
    return result

class Recipes(BaseModel):
    name: str
    description: str
    ingredients:str
    text: str
    time: str

@app.post("/add-recipe")
async def create_recipe(recipes: Recipes):
    collection_recipes.insert_one({
        "name": recipes.name,
        "description": recipes.description,
        "ingredients": recipes.ingredients,
        "text": recipes.text,
        "time": recipes.time,
    })
    return HTTPException(
        status_code=status.HTTP_200_OK,
        detail="Recipe added"
    )

class User(BaseModel):
    login: str
    email: str
    password:str
    role: str

@app.post("/add-user")
async def create_user(user: User):
    test_user = collection_users.count_documents({"login": user.login})
    if test_user != 0:
        return {"error": "login already registered"}
    
    collection_users.insert_one({
        "login": user.login,
        "email": user.email,
        "password_hash": pwd_context.hash(user.password),
        "role": user.role,
    })

    return HTTPException(
        status_code=status.HTTP_200_OK,
        detail="User registered successfully"
    )

class UserAuth(BaseModel):
    login: str
    password:str


@app.post("/test-user")
async def test_user(user: UserAuth):
    count_user = collection_users.count_documents({"login": user.login})
    if count_user == 0:
        return {"error": "invalid login"}
    test_user = collection_users.find_one({"login": user.login})
    if pwd_context.verify(user.password, test_user["password_hash"]):
        return HTTPException(
        status_code=status.HTTP_200_OK,
        detail="User right"
    )
    else:
        return {"error": "invalid password"}