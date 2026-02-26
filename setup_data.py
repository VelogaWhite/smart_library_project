import os
import django
from django.utils import timezone

# ตั้งค่า Environment ให้รู้จัก Django project
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_config.settings')
django.setup()

from library_app.models import Category, Book, User
from django.contrib.auth.hashers import make_password

def run():
    print("🗑️  Cleaning old data...")
    # ลบข้อมูลเก่าทิ้ง (ยกเว้น Superuser ถ้ามี)
    Category.objects.all().delete()
    Book.objects.all().delete()
    User.objects.filter(username__in=['sarah_lib', 'alex_mem']).delete()

    print("📦 Creating Categories...")
    cat_tech = Category.objects.create(CategoryName="Technology")
    cat_sci = Category.objects.create(CategoryName="Science")
    cat_fic = Category.objects.create(CategoryName="Fiction")

    print("📚 Creating Books...")
    books = [
        ("Python for Beginners", cat_tech, "John Doe", "978-0134076251", 5),
        ("Clean Code", cat_tech, "Robert C. Martin", "978-0132350884", 3),
        ("Introduction to Physics", cat_sci, "Halliday", "978-1118230718", 2),
        ("The Great Gatsby", cat_fic, "F. Scott Fitzgerald", "978-0743273565", 4),
    ]

    for title, cat, author, isbn, copies in books:
        Book.objects.create(
            Title=title,
            CategoryID=cat,
            AuthorName=author,
            ISBN=isbn,
            TotalCopies=copies,
            AvailableCopies=copies
        )

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

    print("✅ Mock Data Imported Successfully!")
    print("------------------------------------------------")
    print("   Librarian Login: sarah_lib / password123")
    print("   Member Login:    alex_mem  / password123")
    print("------------------------------------------------")

if __name__ == '__main__':
    run()