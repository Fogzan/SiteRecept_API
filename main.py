from fastapi import FastAPI, HTTPException, status
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from pydantic import BaseModel
import random
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
from bson.objectid import ObjectId

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

# 
# РАБОТА С РЕЦЕПТАМИ
# 

@app.get("/get-all-recipes")
async def getAllRecipes():
    result_find = collection_recipes.find({}, {})
    result = []
    for item in result_find:
        item["_id"] = str(item["_id"])
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
        detail="Recipe added successfully"
    )

@app.delete("/delete-recipe")
async def delete_item(recipe_id: str):
    # Преобразуем item_id в ObjectId
    obj_id = ObjectId(recipe_id)
    
    # Удаляем запись по _id
    result = collection_recipes.delete_one({"_id": obj_id})
    
    # Проверяем, была ли удалена запись
    if result.deleted_count == 1:
        return HTTPException(
            status_code=status.HTTP_200_OK,
            detail="Recipe deleted successfully"
            )
    else:
        return HTTPException(
            status_code=404, 
            detail="Item not found"
            )
    


class ForLike(BaseModel):
    recipe_id: str
    login: str

@app.post("/recipe/set-like")
async def set_like(forLike: ForLike):
    recipe = collection_recipes.find_one({"_id": ObjectId(forLike.recipe_id)})
    if not recipe:
        return {"error": "there is no such recipe"}

    test_user = collection_users.find_one({"login": forLike.login})
    if not test_user:
        return {"error": "invalid login"}

    if forLike.login in recipe.get("likes", []):
        collection_recipes.update_one(
            {"_id": ObjectId(forLike.recipe_id)},
            {"$pull": {"likes": forLike.login}}
        )
        return {
            "status_code": status.HTTP_200_OK,
            "detail": "like was successfully deleted",
            "ction": "delete"
        }

    else:
        collection_recipes.update_one(
            {"_id": ObjectId(forLike.recipe_id)},
            {"$push": {"likes": forLike.login}}
        )
        return {
            "status_code": status.HTTP_200_OK,
            "detail": "like was successfully set",
            "ction": "set"
        }


class ForComment(BaseModel):
    recipe_id: str
    login: str
    date: str
    text: str

@app.post("/recipe/set-comment")
async def set_like(forComment: ForComment):
    recipe = collection_recipes.find_one({"_id": ObjectId(forComment.recipe_id)})
    if not recipe:
        return {"error": "there is no such recipe"}
    
    test_user = collection_users.find_one({"login": forComment.login})
    if not test_user:
        return {"error": "invalid login"}

    collection_recipes.update_one(
            {"_id": ObjectId(forComment.recipe_id)},
            {"$push": {"comments": {
                "login": forComment.login,
                "date": forComment.date,
                "text": forComment.text
            }}}
        )

    return HTTPException(
        status_code=status.HTTP_200_OK,
        detail="comment added successfully"
    )

# 
#   РАБОТА С ПОЛЬЗОВАТЕЛЕМ 
# 

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
        return {
            "status_code": status.HTTP_200_OK,
            "detail": "User right",
            "role": test_user["role"]
        }
    else:
        return {"error": "invalid password"}