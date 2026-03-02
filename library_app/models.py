from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

# ==========================================
# 1. Members (ข้อมูลสมาชิก)
# ==========================================
class Member(models.Model):
    # ใช้ BigIntegerField สำหรับ SSID เพื่อรองรับตัวเลขยาวๆ และใช้สแกน Barcode ได้
    ssid = models.BigIntegerField(primary_key=True, help_text="รหัสสมาชิก (Numeric-only, เช่น 10000001)")
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    is_admin = models.BooleanField(default=False)  # True = บรรณารักษ์, False = สมาชิกทั่วไป
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        role = "Admin" if self.is_admin else "Member"
        return f"[{self.ssid}] {self.full_name} ({role})"


# ==========================================
# 2. Admin Auth (ระบบรหัสผ่านผู้ดูแล)
# ==========================================
class AdminAuth(models.Model):
    # เชื่อมกับตาราง Member แบบ 1-to-1 (เฉพาะคนที่เป็น is_admin=True ถึงจะมาใช้ตารางนี้)
    member = models.OneToOneField(Member, on_delete=models.CASCADE, related_name='auth_profile')
    password_hash = models.CharField(max_length=128)

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def __str__(self):
        return f"Security Profile for Admin: {self.member.full_name}"


# ==========================================
# 3. Books (ข้อมูลหนังสือ)
# ==========================================
class Book(models.Model):
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Maintenance', 'Maintenance'),
        ('Lost', 'Lost'),
    ]

    # เปลี่ยน BookID เป็นตัวเลขเพื่อให้ง่ายต่อการสแกน Barcode ทันทีโดยไม่ต้องมี BookCopy
    book_id = models.BigIntegerField(primary_key=True, help_text="รหัสหนังสือ (Numeric-only)")
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20)
    category = models.CharField(max_length=100) # เก็บเป็น Text แทนเพื่อความเรียบง่ายตาม V5
    location = models.CharField(max_length=100, help_text="เช่น ชั้น A1")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Available')

    def __str__(self):
        return f"[{self.book_id}] {self.title}"


# ==========================================
# 4. Borrow Transactions (ธุรกรรมการยืม-คืน)
# ==========================================
class BorrowTransaction(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'ACTIVE'),
        ('RETURNED', 'RETURNED'),
        ('OVERDUE', 'OVERDUE')
    ]
    
    tx_id = models.BigAutoField(primary_key=True)
    
    # เชื่อมด้วย FK ไปที่ Member และ Book โดยตรง
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='transactions')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='transactions')
    
    start_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')

    # ฟังก์ชันเสริมเพื่อเช็คสถานะ Overdue อัตโนมัติ (Dynamic Property)
    @property
    def is_overdue(self):
        if self.status == 'ACTIVE' and self.due_date < timezone.now():
            return True
        return False

    def __str__(self):
        return f"TX-{self.tx_id} | {self.member.full_name} -> {self.book.title} ({self.status})"