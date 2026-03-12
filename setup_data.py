import os
import django
import random
from django.utils import timezone
from datetime import timedelta

# ตั้งค่า Environment ให้รู้จัก Django project
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_config.settings')
django.setup()

from library_app.models import Member, Book, BorrowTransaction

def run():
    print("🗑️  Cleaning old data...")
    BorrowTransaction.objects.all().delete()
    Book.objects.all().delete()
    Member.objects.all().delete()

    print("👥 Creating Admin & 20 Members...")
    # 1. สร้างบรรณารักษ์ (Admin)
    admin = Member(
        ssid=90000001, 
        full_name="Sarah Librarian", 
        email="admin@lib.com", 
        phone_number="0800000000", 
        is_admin=True
    )
    admin.set_password("admin123")
    admin.save()

    # 2. สร้างสมาชิกทั่วไป 20 คน
    members = []
    for i in range(1, 21):
        m = Member(
            ssid=10000000 + i, 
            full_name=f"Member User {i}", 
            email=f"user{i}@mem.com", 
            phone_number=f"08{random.randint(10000000, 99999999)}", 
            is_admin=False
        )
        m.set_password("member123")
        m.save()
        members.append(m)

    print("📚 Creating 10 Books...")
    categories = ['Technology', 'Science', 'History', 'Fiction', 'Self-Help', 'Business']
    books_data = [
        (10001, "Python Crash Course", "Eric Matthes", "9781593279288", "Technology", "A1"),
        (10002, "Clean Code", "Robert C. Martin", "9780132350884", "Technology", "A1"),
        (10003, "Introduction to Algorithms", "Thomas H.", "9780262033848", "Science", "B1"),
        (10004, "A Brief History of Time", "Stephen Hawking", "9780553380163", "Science", "B2"),
        (10005, "Sapiens", "Yuval Noah Harari", "9780062316097", "History", "C1"),
        (10006, "Guns, Germs, and Steel", "Jared Diamond", "9780393317558", "History", "C2"),
        (10007, "1984", "George Orwell", "9780451524935", "Fiction", "D1"),
        (10008, "To Kill a Mockingbird", "Harper Lee", "9780060935467", "Fiction", "D1"),
        (10009, "Atomic Habits", "James Clear", "9780735211292", "Self-Help", "E1"),
        (10010, "The Lean Startup", "Eric Ries", "9780307887894", "Business", "F1"),
    ]
    
    books = []
    for b_id, title, author, isbn, cat, loc in books_data:
        books.append(Book.objects.create(book_id=b_id, title=title, author=author, isbn=isbn, category=cat, location=loc, status='AVAILABLE'))

    print("🔄 Creating 20 Transactions (6 Available, 1 Active, 3 Overdue)...")
    now = timezone.now()

    # ฟังก์ชันช่วยสุ่มวันที่ย้อนหลัง (ข้ามวันอาทิตย์)
    def get_date_ago(days_min, days_max):
        dt = now - timedelta(days=random.randint(days_min, days_max))
        if dt.weekday() == 6: # ข้ามวันอาทิตย์ (6) ให้ขยับไป 1 วัน
            dt -= timedelta(days=1)
        return dt

    durations_choice = [3, 5, 7, 7, 10, 14]

    # --- แบ่งกลุ่มหนังสือ 10 เล่ม ---
    # สุ่มเลือก 4 เล่มที่จะมีสถานะถูกยืมอยู่ (BORROWED)
    borrowed_books = random.sample(books, 4)
    active_book = borrowed_books[0]        # 1 เล่มที่กำลังยืม (ยังไม่เกินกำหนด)
    overdue_books = borrowed_books[1:4]    # 3 เล่มที่เกินกำหนด
    
    # อีก 6 เล่มที่เหลือให้เป็นหนังสือพร้อมยืม (AVAILABLE)
    available_books = [b for b in books if b not in borrowed_books]

    # เตรียมรายการประวัติ 20 รายการ
    tx_configs = []
    
    # 1. 16 รายการเป็นประวัติการยืมในอดีตและคืนแล้ว (ใช้หนังสือจากกลุ่ม Available)
    for _ in range(16):
        tx_configs.append(('RETURNED', random.choice(available_books)))
        
    # 2. 1 รายการกำลังอยู่ในระยะเวลาการยืม
    tx_configs.append(('ACTIVE', active_book))
    
    # 3. 3 รายการยืมและเกินกำหนดแล้ว
    for b in overdue_books:
        tx_configs.append(('OVERDUE', b))

    # สลับลำดับคนยืมทั้ง 20 คน
    random.shuffle(members)

    # วนลูปสร้างประวัติการยืมทีละรายการ
    for i, (status, book) in enumerate(tx_configs):
        duration = random.choice(durations_choice)
        fine_amount = 0.0
        returned_at = None

        if status == 'RETURNED':
            start_date = get_date_ago(15, 40)
            due_date = start_date + timedelta(days=duration)
            returned_at = start_date + timedelta(days=random.randint(1, duration))
            book.status = 'AVAILABLE'

        elif status == 'OVERDUE':
            # เลยกำหนดมาแล้ว 1-5 วัน
            due_date = get_date_ago(1, 5)
            start_date = due_date - timedelta(days=duration)
            fine_amount = float((now - due_date).days * 10) # ปรับวันละ 10 บาท
            book.status = 'BORROWED'

        else: # ACTIVE
            # พึ่งยืมไป 0-2 วันที่แล้ว (ยังไม่เกินกำหนด)
            start_date = get_date_ago(0, 2)
            due_date = start_date + timedelta(days=duration)
            if due_date <= now: # เซฟโซน ป้องกันการสุ่มพลาดให้ due_date เป็นอดีต
                due_date = now + timedelta(days=3)
            book.status = 'BORROWED'

        # อัปเดตสถานะล่าสุดของหนังสือ
        book.save()

        # สร้างประวัติการยืมลง DB
        BorrowTransaction.objects.create(
            member=members[i],
            book=book,
            start_date=start_date,
            due_date=due_date,
            returned_at=returned_at,
            fine_amount=fine_amount,
            status=status
        )

    print("✅ Mock Data Generated Successfully!")
    print("   - Transactions: 20 records")
    print("   - Available Books: 6 books")
    print("   - Active Borrows: 1 book")
    print("   - Overdue Borrows: 3 books")
    print("👉 For Admin Login: SSID = 90000001, Password = admin123")

if __name__ == '__main__':
    run()