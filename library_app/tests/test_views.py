from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from library_app.models import User, Category, Book, BookCopy, BorrowingRecord

class SmartLibraryV4Tests(TestCase):
    """
    ชุดการทดสอบสำหรับระบบ Smart Library V4.0 (Item-Level Tracking)
    """

    @classmethod
    def setUpTestData(cls):
        # ==========================================
        # 1. สร้างผู้ใช้งานจำลอง (Mock Users)
        # ==========================================
        cls.member = User.objects.create_user(
            username='member_john', 
            password='password123', 
            Role='Member', 
            FullName='John Doe'
        )
        cls.librarian = User.objects.create_user(
            username='lib_sarah', 
            password='password123', 
            Role='Librarian', 
            FullName='Sarah Connor'
        )

        # ==========================================
        # 2. สร้างหมวดหมู่ และ หัวเรื่องหนังสือจำลอง
        # ==========================================
        cls.category = Category.objects.create(CategoryName='Technology')
        cls.book_python = Book.objects.create(
            Title='Python 101', 
            CategoryID=cls.category, 
            AuthorName='Guido', 
            ISBN='978-01'
        )
        cls.book_java = Book.objects.create(
            Title='Java Advanced', 
            CategoryID=cls.category, 
            AuthorName='James', 
            ISBN='978-02'
        )

        # ==========================================
        # 3. สร้างเล่มหนังสือจริง (BookCopy)
        # ==========================================
        # Python 101 มีสต็อก 2 เล่ม (Available)
        cls.python_copy_1 = BookCopy.objects.create(BookID=cls.book_python, Barcode='PY-001', Status='Available')
        cls.python_copy_2 = BookCopy.objects.create(BookID=cls.book_python, Barcode='PY-002', Status='Available')
        
        # Java Advanced ไม่มีสต็อก (ไม่ได้สร้าง BookCopy ให้)

    def setUp(self):
        # เตรียม Client สำหรับจำลองการ Request เข้าเว็บ
        self.member_client = Client()
        self.member_client.force_login(self.member)
        
        self.lib_client = Client()
        self.lib_client.force_login(self.librarian)

    # ==========================================
    # 🧪 TEST GROUP 1: Models & Properties
    # ==========================================
    def test_book_property_counts_available_copies_correctly(self):
        """
        ทดสอบว่า @property available_copies และ total_copies นับจำนวนจากตาราง BookCopy ถูกต้อง
        """
        # Python ควรมี 2 เล่ม (ว่าง 2) / Java ควรมี 0 เล่ม
        self.assertEqual(self.book_python.total_copies, 2)
        self.assertEqual(self.book_python.available_copies, 2)
        
        self.assertEqual(self.book_java.total_copies, 0)
        self.assertEqual(self.book_java.available_copies, 0)

    # ==========================================
    # 🧪 TEST GROUP 2: Business Logic - Member
    # ==========================================
    def test_member_can_request_borrow_and_status_is_pending(self):
        """
        ทดสอบว่า Member ส่งคำร้องยืมสำเร็จ และสร้าง BorrowingRecord สถานะ Pending
        """
        url = reverse('borrow_book', args=[self.book_python.id])
        initial_stock = self.book_python.available_copies

        # Member กดส่งคำร้องขอยืม
        response = self.member_client.post(url)

        # เช็กผลลัพธ์ว่าสร้าง Record สำเร็จ และสต็อกยังไม่ถูกตัดจนกว่าบรรณารักษ์จะอนุมัติ
        self.assertEqual(BorrowingRecord.objects.count(), 1)
        record = BorrowingRecord.objects.first()
        self.assertEqual(record.Status, 'Pending')
        self.assertIsNone(record.BookCopyID) # ยังไม่ผูกกับเล่มจริง
        self.assertEqual(self.book_python.available_copies, initial_stock)
        self.assertRedirects(response, reverse('search_books'))

    # ==========================================
    # 🧪 TEST GROUP 3: Business Logic - Librarian
    # ==========================================
    def test_librarian_can_approve_borrow_and_reduces_available_copies(self):
        """
        ทดสอบว่าบรรณารักษ์อนุมัติคำร้อง -> ตัดสต็อกสำเร็จ -> ผูกเล่มหนังสือจริงเข้ากับ Record
        """
        pending_record = BorrowingRecord.objects.create(
            UserID=self.member, BookID=self.book_python, Status='Pending'
        )
        url = reverse('approve_borrow', args=[pending_record.id])

        # บรรณารักษ์กด Approve
        self.lib_client.post(url)
        
        pending_record.refresh_from_db()

        self.assertEqual(pending_record.Status, 'Active')
        self.assertIsNotNone(pending_record.BookCopyID) # ต้องมีการแจกจ่ายเล่มจริงให้แล้ว
        self.assertEqual(pending_record.BookCopyID.Status, 'Borrowed')
        self.assertEqual(self.book_python.available_copies, 1) # สต็อกว่างต้องลดลง 1

    def test_librarian_can_reject_request(self):
        """
        ทดสอบบรรณารักษ์กดปฏิเสธ -> คำร้องเป็น Rejected
        """
        pending_record = BorrowingRecord.objects.create(
            UserID=self.member, BookID=self.book_python, Status='Pending'
        )
        url = reverse('reject_borrow', args=[pending_record.id])

        # บรรณารักษ์กด Reject
        self.lib_client.post(url)
        pending_record.refresh_from_db()

        self.assertEqual(pending_record.Status, 'Rejected')
        self.assertEqual(self.book_python.available_copies, 2) # สต็อกต้องเท่าเดิม

    def test_librarian_can_process_return_and_restores_stock(self):
        """
        ทดสอบรับคืนหนังสือ -> สถานะเปลี่ยนเป็น Returned -> เล่มหนังสือกลับมา Available
        """
        # จำลองการยืมที่กำลัง Active อยู่
        self.python_copy_1.Status = 'Borrowed'
        self.python_copy_1.save()
        
        active_record = BorrowingRecord.objects.create(
            UserID=self.member, 
            BookID=self.book_python, 
            BookCopyID=self.python_copy_1,
            Status='Active',
            DueDate=timezone.now() + timedelta(days=7)
        )
        url = reverse('return_book', args=[active_record.id])

        # บรรณารักษ์กดรับคืน
        self.lib_client.post(url)
        
        active_record.refresh_from_db()
        self.python_copy_1.refresh_from_db()

        self.assertEqual(active_record.Status, 'Returned')
        self.assertIsNotNone(active_record.ReturnDate)
        self.assertEqual(self.python_copy_1.Status, 'Available') # เล่มจริงกลับมาตีเข้าสต็อก
        self.assertEqual(self.book_python.available_copies, 2) # สต็อกรวมกลับมาเต็ม 2 เล่ม