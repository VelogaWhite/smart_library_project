from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
# อัปเดตการ Import Model ตาม V4.0 (ลบ TotalCopies เพิ่ม BookCopy)
from library_app.models import Book, Category, BookCopy, BorrowingRecord
from datetime import timedelta
from django.utils import timezone

User = get_user_model()

class TypicalDaySystemTestV4(TestCase):
    def setUp(self):
        # 1. เตรียมข้อมูลพื้นฐาน (หมวดหมู่ และ หนังสือ)
        self.category = Category.objects.create(CategoryName="Technology")
        
        self.book = Book.objects.create(
            Title="Python for Beginners",
            CategoryID=self.category,
            AuthorName="John Doe",
            ISBN="123456789"
            # ไม่ใช้ TotalCopies และ AvailableCopies แล้ว
        )

        # 2. จำลอง Physical Books (หนังสือตัวเป็นๆ ที่มีบาร์โค้ด)
        self.copy1 = BookCopy.objects.create(BookID=self.book, Barcode="BC-PY-001", Status="Available")
        self.copy2 = BookCopy.objects.create(BookID=self.book, Barcode="BC-PY-002", Status="Available")

        # 3. เตรียม User Accounts
        # Sarah - Librarian
        self.sarah = User.objects.create_user(
            username='sarah_lib', 
            password='password123', 
            Role='Librarian',
            FullName='Sarah Connor'
        )
        
        # Alex - Member
        self.alex = User.objects.create_user(
            username='alex_mem', 
            password='password123', 
            Role='Member',
            FullName='Alex Murphy'
        )

        # 4. จำลอง Browser Clients (และ Login ไว้ล่วงหน้า)
        self.sarah_client = Client()
        self.sarah_client.force_login(self.sarah)

        self.alex_client = Client()
        self.alex_client.force_login(self.alex)

    def test_a_typical_day_using_v4_system(self):
        """
        Integration Test ตาม User Stories ของระบบ Version 4.0
        """
        # ==========================================
        # SCENE 1: Member ค้นหาและส่งคำร้องขอยืม (Request)
        # ==========================================
        # Alex ค้นหาหนังสือ
        response = self.alex_client.get(reverse('search_books') + '?q=Python')
        self.assertContains(response, 'Python for Beginners')

        # Alex กด Request Borrow
        self.alex_client.post(reverse('borrow_book', args=[self.book.id]))
        
        # ตรวจสอบสถานะ: ต้องเกิด Record ที่เป็น Pending และยังไม่ถูกผูกบาร์โค้ด
        borrow_record = BorrowingRecord.objects.get(UserID=self.alex, BookID=self.book)
        self.assertEqual(borrow_record.Status, 'Pending')
        self.assertIsNone(borrow_record.BookCopyID)

        # ==========================================
        # SCENE 2: Librarian อนุมัติด้วยบาร์โค้ด (Barcode Checkout)
        # ==========================================
        # Sarah เห็นคำร้อง และหยิบเล่ม "BC-PY-001" มาสแกนอนุมัติ
        self.sarah_client.post(reverse('approve_borrow', args=[borrow_record.id]), {
            'barcode': 'BC-PY-001' # POST payload สำหรับ V4.0
        })
        
        # Refresh ข้อมูลจากฐานข้อมูล
        borrow_record.refresh_from_db()
        self.copy1.refresh_from_db()

        # ตรวจสอบสถานะ: Record ต้องเป็น Active, ผูกกับ Copy1 และเล่มนั้นสถานะต้องเปลี่ยนเป็น Borrowed
        self.assertEqual(borrow_record.Status, 'Active')
        self.assertEqual(borrow_record.BookCopyID, self.copy1)
        self.assertEqual(self.copy1.Status, 'Borrowed')

        # ==========================================
        # SCENE 3: Member กดต่ออายุหนังสือ (Self-Renew)
        # ==========================================
        original_due_date = borrow_record.DueDate
        
        # Alex เข้ามาหน้าประวัติแล้วกดปุ่ม Renew
        self.alex_client.post(reverse('renew_book', args=[borrow_record.id]))
        
        borrow_record.refresh_from_db()
        
        # ตรวจสอบสถานะ: ตัวนับการต่ออายุเพิ่มขึ้น และวันคืนถูกยืดออกไป
        self.assertEqual(borrow_record.RenewCount, 1)
        self.assertTrue(borrow_record.DueDate > original_due_date)

        # ==========================================
        # SCENE 4: Librarian กดรับคืน (Return & Restock)
        # ==========================================
        # Sarah สแกน/กดรับคืนหนังสือ
        self.sarah_client.post(reverse('return_book', args=[borrow_record.id]))
        
        borrow_record.refresh_from_db()
        self.copy1.refresh_from_db()

        # ตรวจสอบสถานะ: Record ปิดแล้ว และหนังสือเล่มจริงถูกดันกลับมาเป็น Available
        self.assertEqual(borrow_record.Status, 'Returned')
        self.assertIsNotNone(borrow_record.ReturnDate)
        self.assertEqual(self.copy1.Status, 'Available')