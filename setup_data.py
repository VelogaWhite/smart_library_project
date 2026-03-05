import os
import django
from django.utils import timezone
from datetime import timedelta

# ตั้งค่า Environment ให้รู้จัก Django project
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_config.settings')
django.setup()

from library_app.models import Member, Book, BorrowTransaction, AdminAuth

def run():
    print("🗑️  Cleaning old data...")
    BorrowTransaction.objects.all().delete()
    Book.objects.all().delete()
    AdminAuth.objects.all().delete()
    Member.objects.all().delete()

    print("👥 Creating Admin & Members (V5.0 SSID)...")
    # 1. สร้างบรรณารักษ์ (Admin)
    admin = Member.objects.create(
        ssid=90000001, 
        full_name="Sarah Librarian", 
        email="admin@lib.com", 
        phone_number="0800000000", 
        is_admin=True
    )
    admin_auth = AdminAuth(member=admin)
    admin_auth.set_password("admin123")
    admin_auth.save()

    # 2. สร้างสมาชิกทั่วไป 3 คน
    m1 = Member.objects.create(ssid=10000001, full_name="Alice Wonderland", email="alice@mem.com", phone_number="0811111111", is_admin=False)
    m2 = Member.objects.create(ssid=10000002, full_name="Bob Builder", email="bob@mem.com", phone_number="0822222222", is_admin=False)
    m3 = Member.objects.create(ssid=10000003, full_name="Charlie Brown", email="charlie@mem.com", phone_number="0833333333", is_admin=False)

    print("📚 Creating 10 Books...")
    books_data = [
        (10001, "Python Crash Course", "Eric Matthes", "9781593279288", "Technology", "A1", "Available"),
        (10002, "Clean Code", "Robert C. Martin", "9780132350884", "Technology", "A1", "Borrowed"),
        (10003, "The Pragmatic Programmer", "Andrew Hunt", "9780135957059", "Technology", "A2", "Available"),
        (10004, "Design Patterns", "Erich Gamma", "9780201633610", "Technology", "A2", "Borrowed"),
        (10005, "Introduction to Algorithms", "Thomas H. Cormen", "9780262033848", "Science", "B1", "Available"),
        (10006, "Sapiens", "Yuval Noah Harari", "9780062316097", "History", "C1", "Available"),
        (10007, "1984", "George Orwell", "9780451524935", "Fiction", "D1", "Returned"),
        (10008, "To Kill a Mockingbird", "Harper Lee", "9780060935467", "Fiction", "D1", "Available"),
        (10009, "The Great Gatsby", "F. Scott Fitzgerald", "9780743273565", "Fiction", "D2", "Available"),
        (10010, "Atomic Habits", "James Clear", "9780735211292", "Self-Help", "E1", "Available"),
    ]
    books = []
    for b_id, title, author, isbn, cat, loc, status in books_data:
        # หาก status เป็น Borrowed/Returned ให้ตั้งเป็น Borrowed เพื่อให้สมจริงใน Transactions
        actual_status = 'Borrowed' if status in ['Borrowed', 'Returned'] else 'Available'
        books.append(Book.objects.create(book_id=b_id, title=title, author=author, isbn=isbn, category=cat, location=loc, status=actual_status))

    print("🔄 Creating Transactions (Active, Returned, Overdue)...")
    now = timezone.now()

    # ยืมปกติ (ACTIVE) - m1 ยืม Clean Code
    BorrowTransaction.objects.create(member=m1, book=books[1], due_date=now + timedelta(days=5), status='ACTIVE')
    
    # เกินกำหนด (OVERDUE) เพื่อให้กราฟิก Dashboard โชว์ - m2 ยืม Design Patterns
    BorrowTransaction.objects.create(member=m2, book=books[3], due_date=now - timedelta(days=3), fine_amount=30.00, status='OVERDUE')
    
    # คืนแล้ว (RETURNED) - m3 ยืม 1984 
    tx_returned = BorrowTransaction.objects.create(member=m3, book=books[6], due_date=now - timedelta(days=7), returned_at=now - timedelta(days=5), status='RETURNED')
    # ปรับสถานะหนังสือที่คืนแล้วกลับเป็น Available
    tx_returned.book.status = 'Available'
    tx_returned.book.save()

    print("✅ Mock Data Generated Successfully!")
    print("👉 For Admin Login: SSID = 90000001, Password = admin123")
    print("👉 For Member Login: SSID = 10000001")

if __name__ == '__main__':
    run()