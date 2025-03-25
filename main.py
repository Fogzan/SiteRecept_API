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
collection_collections = db['collections']

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

#-----------------------------------------------------------------------------------------------------------------------------------------
# РАБОТА С РЕЦЕПТАМИ
#-----------------------------------------------------------------------------------------------------------------------------------------

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
    user_login: str

@app.post("/add-recipe")
async def create_recipe(recipes: Recipes):
    collection_recipes.insert_one({
        "name": recipes.name,
        "description": recipes.description,
        "ingredients": recipes.ingredients,
        "text": recipes.text,
        "time": recipes.time,
        "creator": recipes.user_login,
        "likes": [],
        "comments": [],
    })
    return HTTPException(
        status_code=status.HTTP_200_OK,
        detail="Recipe added successfully"
    )

@app.post("/delete-recipe")
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
    
#-----------------------------------------------------------------------------------------------------------------------------------------
# РАБОТА С ФУНКЦИОНАЛОМ
#-----------------------------------------------------------------------------------------------------------------------------------------

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

#-----------------------------------------------------------------------------------------------------------------------------------------
#   РАБОТА С ПОЛЬЗОВАТЕЛЕМ 
#-----------------------------------------------------------------------------------------------------------------------------------------

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
        "collections": [],
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
    
#-----------------------------------------------------------------------------------------------------------------------------------------
# РАБОТА С КОЛЛЕКЦИЯМИ
#-----------------------------------------------------------------------------------------------------------------------------------------

class AddCollection(BaseModel):
    name: str
    login: str

@app.post("/add-collection")
async def add_collection(collection: AddCollection):
    user = collection_users.find_one({"login": collection.login})
    if not user:
        return HTTPException(
            status_code=404,
            detail="User not found"
        )
    result = collection_collections.insert_one({
        "name": collection.name,
        "recipes_ids": [],
    })
    collection_users.update_one(
        {"_id": user["_id"]},
        {"$push": {"collections": str(result.inserted_id)}}
    )
    return {
        "status": "Collection added successfully",
        "collection_id": str(result.inserted_id),
    }

class RemoveCollection(BaseModel):
    id: str
    login: str

@app.post("/remove-collection")
async def remove_collection(collection: RemoveCollection):
    user = collection_users.find_one({"login": collection.login})
    if not user:
        return HTTPException(
            status_code=404,
            detail="User not found"
        )
    result = collection_collections.find_one({"_id": ObjectId(collection.id)})
    if not result:
        return HTTPException(
            status_code=404,
            detail="Collection not found"
        )   

    collection_users.update_one(
        {"_id": user["_id"]},
        {"$pull": {"collections": collection.id}}
    )
    collection_collections.delete_one({"_id": ObjectId(collection.id)})

    return {
        "status": "Collection remove successfully"
    }

class AddToCollection(BaseModel):
    id_collection: str
    id_recipe: str

@app.post("/add-to-collection")
async def add_to_collection(collection: AddToCollection):
    result = collection_collections.find_one({"_id": ObjectId(collection.id_collection)})
    if not(result):
        return HTTPException(
            status_code=404,
            detail="Collection not found"
        )
    result = collection_recipes.find_one({"_id": ObjectId(collection.id_recipe)})
    if not(result):
        return HTTPException(
            status_code=404,
            detail="Recipe not found"
        )
    collection_collections.update_one(
        {"_id": ObjectId(collection.id_collection)},
        {"$push": {"recipes_ids": str(collection.id_recipe)}}
    )
    return {
        "status": "Recipe to collection added successfully"
    }

@app.post("/remove-from-collection")
async def remove_from_collection(collection: AddToCollection):
    result = collection_collections.find_one({"_id": ObjectId(collection.id_collection)})
    if not(result):
        return HTTPException(
            status_code=404,
            detail="Collection not found"
        )
    if not(collection.id_recipe in result["recipes_ids"]):
        return HTTPException(
            status_code=404,
            detail="Collection not have its recipe"
        )
    collection_collections.update_one(
        {"_id": ObjectId(collection.id_collection)},
        {"$pull": {"recipes_ids": str(collection.id_recipe)}}
    )
    return {
        "status": "Recipe from collection remove successfully"
    }