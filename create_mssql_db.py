import pyodbc
import environ

env = environ.Env()
environ.Env.read_env('.env')

server = env('MSSQL_HOST', default=r'localhost')
driver = env('MSSQL_DRIVER', default='ODBC Driver 18 for SQL Server')

# เชื่อมต่อไปที่ฐานข้อมูลโดยใช้ Windows Authentication (Trusted_Connection=yes)
conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE=master;Trusted_Connection=yes;TrustServerCertificate=yes;"

try:
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()
    
    # เช็คว่ามีฐานข้อมูลหรือยัง ถ้ายังไม่มีให้สร้างใหม่
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'library_db')
        BEGIN
            CREATE DATABASE library_db;
        END
    """)
    print("✅ สร้างก้อนฐานข้อมูล 'library_db' ด้วย Windows Authentication สำเร็จแล้ว!")
    conn.close()
    
except Exception as e:
    print("❌ เกิดข้อผิดพลาด:", e)