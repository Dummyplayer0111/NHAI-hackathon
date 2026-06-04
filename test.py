from pymongo import MongoClient

client = MongoClient(
    "YOUR_CONNECTION_STRING"
)

db = client["attendance_db"]

collection = db["attendance"]

collection.insert_one({
    "name": "Divyanth",
    "status": "test"
})

print("Connected!")