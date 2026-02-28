from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = [('Librarian', 'Librarian'), ('Member', 'Member')]
    Role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Member')
    FullName = models.CharField(max_length=255, blank=True, default='')

class Category(models.Model):
    CategoryName = models.CharField(max_length=100)
    def __str__(self): return self.CategoryName

class Book(models.Model):
    Title = models.CharField(max_length=255)
    CategoryID = models.ForeignKey(Category, on_delete=models.CASCADE)
    AuthorName = models.CharField(max_length=255, default='Unknown')
    ISBN = models.CharField(max_length=20, unique=True)
    # 🚨 ลบฟิลด์ TotalCopies และ AvailableCopies ออกแล้วตามแผน V4.0
    
    # 🔥 เพิ่ม @property เพื่อให้นับจำนวนเล่มจริงจากตาราง BookCopy แบบ Real-time
    @property
    def available_copies(self):
        return self.bookcopy_set.filter(Status='Available').count()
        
    @property
    def total_copies(self):
        return self.bookcopy_set.count()

    def __str__(self): return self.Title

# ==========================================
# 🔥 ตารางใหม่ (V4.0): ข้อมูลหนังสือรายเล่ม (Item Level)
# ==========================================
class BookCopy(models.Model):
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Borrowed', 'Borrowed'),
        ('Lost', 'Lost'),
        ('Maintenance', 'Maintenance')
    ]
    BookID = models.ForeignKey(Book, on_delete=models.CASCADE)
    Barcode = models.CharField(max_length=50, unique=True) # รหัสบาร์โค้ดแปะหลังเล่ม
    Status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Available')

    def __str__(self):
        return f"{self.Barcode} - {self.BookID.Title} ({self.Status})"

# ==========================================
# 🔄 ตารางอัปเดต (V4.0): ธุรกรรมการยืม-คืน
# ==========================================
class BorrowingRecord(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Active', 'Active'),
        ('Returned', 'Returned'),
        ('Rejected', 'Rejected')
    ]
    UserID = models.ForeignKey(User, on_delete=models.CASCADE)
    BookID = models.ForeignKey(Book, on_delete=models.CASCADE)
    
    # 🔥 ฟิลด์ใหม่: ผูกกับเล่มหนังสือจริงเมื่อบรรณารักษ์สแกนบาร์โค้ดอนุมัติ
    BookCopyID = models.ForeignKey(BookCopy, on_delete=models.SET_NULL, null=True, blank=True)
    
    BorrowDate = models.DateTimeField(auto_now_add=True)
    DueDate = models.DateTimeField(null=True, blank=True)
    ReturnDate = models.DateTimeField(null=True, blank=True)
    Status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    # 🔥 ฟิลด์ใหม่: ตัวนับจำนวนครั้งที่ Member กดต่ออายุ (Renew)
    RenewCount = models.IntegerField(default=0)

    def is_overdue(self):
        from django.utils import timezone
        if self.DueDate and not self.ReturnDate:
            return timezone.now() > self.DueDate
        return False

    def __str__(self):
        return f"{self.UserID.username} borrowed {self.BookID.Title} ({self.Status})"

class Fine(models.Model):
    BorrowID = models.ForeignKey(BorrowingRecord, on_delete=models.CASCADE)
    FineAmount = models.DecimalField(max_digits=10, decimal_places=2)
    Status = models.CharField(max_length=20, default='Unpaid')