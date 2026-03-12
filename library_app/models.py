from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import timedelta

# ==========================================
# 1. Members (ข้อมูลสมาชิกและระบบ Auth)
# ==========================================
class Member(models.Model):
    ssid = models.BigIntegerField(primary_key=True, help_text="รหัสสมาชิก (Numeric-only, เช่น 10000001)")
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    
    # แยก Role ชัดเจน
    is_admin = models.BooleanField(default=False)
    
    # ฟิลด์รหัสผ่านรองรับผู้ใช้ทุกคน
    password_hash = models.CharField(max_length=128, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ฟังก์ชันสำหรับเข้ารหัสและตรวจสอบรหัสผ่าน
    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        if not self.password_hash:
            return False
        return check_password(raw_password, self.password_hash)

    def __str__(self):
        role = "Admin" if self.is_admin else "Member"
        return f"[{self.ssid}] {self.full_name} ({role})"


# ==========================================
# 2. Books (ข้อมูลหนังสือ)
# ==========================================
class Book(models.Model):
    book_id = models.BigIntegerField(primary_key=True, help_text="รหัสหนังสือ (Numeric-only สำหรับสแกน)")
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20, null=True, blank=True)
    category = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('BORROWED', 'Borrowed'),
        ('MAINTENANCE', 'Maintenance'),
        ('LOST', 'Lost'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')

    def __str__(self):
        return f"[{self.book_id}] {self.title}"


# ==========================================
# 3. Borrow Transactions (ธุรกรรมการยืม-คืน)
# ==========================================
class BorrowTransaction(models.Model):
    tx_id = models.AutoField(primary_key=True)
    
    # ใช้ db_column เพื่อรักษาชื่อคอลัมน์ใน DB ให้ตรงกับ schema เดิม (ssid, book_id)
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='transactions', db_column='ssid')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='transactions', db_column='book_id')
    
    start_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)
    
    fine_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('RETURNED', 'Returned'),
        ('OVERDUE', 'Overdue'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')

    def save(self, *args, **kwargs):
        # คำนวณวันคืนอัตโนมัติ (สมมติว่ายืมได้ 7 วัน) ถ้าไม่ได้กำหนดมา
        if not self.due_date:
            self.due_date = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"TX-{self.tx_id} | {self.member.full_name} -> {self.book.title}"