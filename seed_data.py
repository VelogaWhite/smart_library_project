from django.utils import timezone
from datetime import timedelta
from library_app.models import Member, Book, BorrowTransaction

# ── สร้าง Member เพิ่ม ──────────────────────────────────────
member_a = Member.objects.create(
    ssid=10000002,
    full_name="Somying Rakdee",
    email="somying@test.com",
    phone_number="0812222222",
    is_admin=False
)

member_b = Member.objects.create(
    ssid=10000003,
    full_name="Wichai Jaikla",
    email="wichai@test.com",
    phone_number="0813333333",
    is_admin=False
)

# ── สร้าง Book ───────────────────────────────────────────────
book_1 = Book.objects.create(
    book_id=1001,
    title="Django for Beginners",
    author="William Vincent",
    isbn="1234567890",
    category="Technology",
    location="A1",
    status="Available"
)

book_2 = Book.objects.create(
    book_id=1002,
    title="Python Crash Course",
    author="Eric Matthes",
    isbn="0987654321",
    category="Technology",
    location="A2",
    status="Available"
)

book_3 = Book.objects.create(
    book_id=1003,
    title="Clean Code",
    author="Robert C. Martin",
    isbn="1122334455",
    category="Technology",
    location="A3",
    status="Available"
)

now = timezone.now()

# ── ACTIVE (ยืมอยู่ ยังไม่เกินกำหนด) ────────────────────────
BorrowTransaction.objects.create(
    member=member_a,
    book=book_1,
    due_date=now + timedelta(days=7),
    returned_at=None,
    fine_amount=0,
    status="ACTIVE"
)

# ── OVERDUE (เกินกำหนดแล้ว) ──────────────────────────────────
BorrowTransaction.objects.create(
    member=member_a,
    book=book_2,
    due_date=now - timedelta(days=5),
    returned_at=None,
    fine_amount=50,
    status="OVERDUE"
)

BorrowTransaction.objects.create(
    member=member_b,
    book=book_3,
    due_date=now - timedelta(days=10),
    returned_at=None,
    fine_amount=100,
    status="OVERDUE"
)

# ── RETURNED (คืนแล้ว) ───────────────────────────────────────
BorrowTransaction.objects.create(
    member=member_b,
    book=book_1,
    due_date=now - timedelta(days=3),
    returned_at=now - timedelta(days=1),
    fine_amount=0,
    status="RETURNED"
)

print("✅ สร้างข้อมูลสำเร็จ!")