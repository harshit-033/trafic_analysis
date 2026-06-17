from pymongo import MongoClient

client = MongoClient("mongodb://admin:admin123@localhost:27017/")
db = client["autoroute"]
collection = db["detections"]

collection.insert_one({"junction": "J1", "vehicles": 23})
print(list(collection.find()))
