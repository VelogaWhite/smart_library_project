import os
import django

# ตั้งค่า Environment ให้รู้จัก Django project
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_config.settings')
django.setup()

from library_app.models import Category, Book, User, BookCopy
from django.contrib.auth.hashers import make_password

def run():
    print("🗑️  Cleaning old data...")
    # การลบ Category และ Book จะเป็นการลบข้อมูลลูก (BookCopy, BorrowingRecord) ทิ้งไปด้วย (Cascade)
    Category.objects.all().delete()
    Book.objects.all().delete()
    User.objects.filter(username__in=['sarah_lib', 'alex_mem']).delete()

    print("📦 Creating Categories...")
    cat_tech = Category.objects.create(CategoryName="Technology")
    cat_sci = Category.objects.create(CategoryName="Science")
    cat_fic = Category.objects.create(CategoryName="Fiction")

    print("📚 Creating Books and Physical Copies (V4.0)...")
    books_data = [
        # (ชื่อเรื่อง, หมวดหมู่, ผู้แต่ง, ISBN, จำนวนเล่มที่จะสร้าง)
        ("Python for Beginners", cat_tech, "John Doe", "978-0134076251", 3),
        ("Clean Code", cat_tech, "Robert C. Martin", "978-0132350884", 2),
        ("Introduction to Physics", cat_sci, "Halliday", "978-1118230718", 2),
        ("The Great Gatsby", cat_fic, "F. Scott Fitzgerald", "978-0743273565", 1),
    ]

    barcode_counter = 1000 # ตัวแปรช่วยรันเลขบาร์โค้ด

    for title, cat, author, isbn, copies in books_data:
        # 1. สร้าง Book (ชื่อเรื่อง / Title Level)
        new_book = Book.objects.create(
            Title=title,
            CategoryID=cat,
            AuthorName=author,
            ISBN=isbn
            # ลบฟิลด์ TotalCopies/AvailableCopies ออกแล้ว
        )
        
        # 2. สร้าง BookCopy (เล่มหนังสือจริง / Item Level) ตามจำนวน copies ที่กำหนด
        for _ in range(copies):
            # สร้าง Barcode เช่น BC-6251-1000
            barcode_str = f"BC-{isbn[-4:]}-{barcode_counter}"
            BookCopy.objects.create(
                BookID=new_book,
                Barcode=barcode_str,
                Status='Available'
            )
            barcode_counter += 1

    print("👥 Creating Users...")
    # Librarian Account
    if not User.objects.filter(username='sarah_lib').exists():
        User.objects.create(
            username='sarah_lib',
            password=make_password('password123'),
            Role='Librarian',
            FullName='Sarah Connor (Librarian)',
            email='sarah@lib.com'
        )
    
    # Member Account
    if not User.objects.filter(username='alex_mem').exists():
        User.objects.create(
            username='alex_mem',
            password=make_password('password123'),
            Role='Member',
            FullName='Alex Murphy (Member)',
            email='alex@mem.com'
        )

    print("✅ Mock Data Generation Completed for V4.0!")
    print(f"📊 Summary: {Book.objects.count()} Books, {BookCopy.objects.count()} Physical Copies, 2 Users.")

if __name__ == '__main__':
    run()