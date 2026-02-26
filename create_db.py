import environ
import MySQLdb

# ดึงค่ารหัสผ่านและ user จากไฟล์ .env ของคุณมาใช้โดยอัตโนมัติ
env = environ.Env()
environ.Env.read_env('.env')

try:
    # วิ่งไปเคาะประตูเซิร์ฟเวอร์ฐานข้อมูลโดยตรง
    conn = MySQLdb.connect(
        host=env('MARIADB_HOST', default='127.0.0.1'),
        user=env('MARIADB_USER', default='root'),
        passwd=env('MARIADB_PASSWORD', default=''),
        port=int(env('MARIADB_PORT', default=3306))
    )
    cursor = conn.cursor()
    # สั่งให้สร้างฐานข้อมูลชื่อ library_db
    cursor.execute("CREATE DATABASE IF NOT EXISTS library_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    print("✅ สร้างก้อนฐานข้อมูล 'library_db' สำเร็จแล้ว! ยินดีด้วยครับ")
    conn.close()
    
except Exception as e:
    print("❌ เกิดข้อผิดพลาด:", e)