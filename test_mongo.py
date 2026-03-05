import pymongo

# 1. เชื่อมต่อ MongoDB (เปลี่ยน URI ตามของจริงของคุณ)
client = pymongo.MongoClient("mongodb://localhost:27017/")

# 2. สร้าง/เลือก Database ชื่อ library_mongo_db
db = client["library_mongo_db"]

# 3. สร้าง/เลือก Collection ชื่อ books (เทียบเท่ากับตารางใน SQL)
books_collection = db["books"]

# 4. ทดลอง Insert ข้อมูล (ข้อดีของ MongoDB คือไม่ต้องมี Schema ตายตัว)
book_data = {
    "book_id": "80000001",
    "title": "Python for Data Science",
    "author": "John Doe",
    "details": {
        "pages": 350,
        "language": "English"
    } # สามารถซ้อนข้อมูลแบบ JSON ได้เลย ซึ่ง SQL ทำได้ยากกว่า
}

# สั่งบันทึกข้อมูล
books_collection.insert_one(book_data)
print("✅ เพิ่มข้อมูลหนังสือลง MongoDB สำเร็จ!")

# 5. ทดลองดึงข้อมูลมาแสดงผล
for book in books_collection.find():
    print("📖 หนังสือที่พบ:", book)