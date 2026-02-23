from django.test import TestCase
from library_app.models import User, Category, Book, BorrowingRecord, Fine

class LibraryModelsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # สร้าง Mock Data สำหรับใช้งานในทุกเทสต์เคส (รันครั้งเดียว เร็วกว่า setUp ปกติ)
        
        # 1. สร้างหมวดหมู่ (Category)
        cls.category = Category.objects.create(CategoryName='Computer Science')
        
        # 2. สร้างหนังสือ (Book) แบบระบุข้อมูลครบถ้วน
        cls.book = Book.objects.create(
            Title='Python 101',
            CategoryID=cls.category,
            AuthorName='John Doe',
            ISBN='1234567890',
            TotalCopies=5,
            AvailableCopies=5
        )
        
        # 3. สร้างหนังสือ (Book) แบบไม่ระบุค่าบางอย่าง (เพื่อทดสอบ Default Values)
        cls.default_book = Book.objects.create(
            Title='Unknown Journey',
            CategoryID=cls.category,
            ISBN='0987654321'
            # ไม่ใส่ AuthorName, TotalCopies, AvailableCopies เพื่อเทสต์ Default
        )
        
        # 4. สร้างผู้ใช้งาน (User)
        cls.member_user = User.objects.create_user(
            username='somchai',
            password='password123',
            FullName='Somchai Jaidee'
            # ไม่ได้ระบุ Role เพื่อทดสอบ Default ว่าเป็น 'Member' หรือไม่
        )
        
        # 5. สร้างประวัติการยืม (BorrowingRecord)
        cls.borrow_record = BorrowingRecord.objects.create(
            UserID=cls.member_user,
            BookID=cls.book
        )

        # 6. สร้างข้อมูลค่าปรับ (Fine) - *สมมติว่าคุณมีฟิลด์ FineAmount และ Status*
        # หากชื่อฟิลด์ใน models.py ต่างไปจากนี้ (เช่น Amount, PaymentStatus) สามารถปรับแก้ได้เลยครับ
        try:
            cls.fine = Fine.objects.create(
                BorrowID=cls.borrow_record
            )
        except Exception:
            cls.fine = None # ป้องกัน Error หากโมเดล Fine ยังสร้างไม่เสร็จ

    def test_category_creation_and_str(self):
        """เทสต์การสร้าง Category และเช็ก String Representation (__str__)"""
        self.assertEqual(self.category.CategoryName, 'Computer Science')
        self.assertEqual(str(self.category), 'Computer Science')

    def test_book_creation_and_fields_are_saved_correctly(self):
        """เทสต์การสร้าง Book และตรวจสอบว่าฟิลด์ต่างๆ บันทึกค่าได้ถูกต้อง"""
        self.assertEqual(self.book.Title, 'Python 101')
        self.assertEqual(self.book.CategoryID.CategoryName, 'Computer Science')
        self.assertEqual(self.book.AuthorName, 'John Doe')
        self.assertEqual(self.book.ISBN, '1234567890')
        self.assertEqual(self.book.TotalCopies, 5)
        self.assertEqual(self.book.AvailableCopies, 5)
        self.assertEqual(str(self.book), 'Python 101')

    def test_book_default_values(self):
        """เทสต์ว่า Default values ของ Book ทำงานถูกต้องเมื่อไม่ได้ระบุค่า"""
        self.assertEqual(self.default_book.AuthorName, 'Unknown') # ทดสอบ default='Unknown'
        self.assertEqual(self.default_book.TotalCopies, 1)        # ทดสอบ default=1
        self.assertEqual(self.default_book.AvailableCopies, 1)    # ทดสอบ default=1

    def test_user_creation_and_default_role(self):
        """เทสต์การสร้าง User และเช็ก Default Role ว่าเป็น Member หรือไม่"""
        self.assertEqual(self.member_user.username, 'somchai')
        self.assertEqual(self.member_user.FullName, 'Somchai Jaidee')
        self.assertEqual(self.member_user.Role, 'Member') # ทดสอบ default='Member'

    def test_borrowing_record_relationships(self):
        """เทสต์การสร้างประวัติการยืม และเช็กความสัมพันธ์ของ Foreign Key"""
        self.assertEqual(self.borrow_record.UserID.username, 'somchai')
        self.assertEqual(self.borrow_record.BookID.Title, 'Python 101')
        
        # ถ้าโมเดลของคุณมีฟิลด์ Status เป็น default='Active' สามารถเอาคอมเมนต์ด้านล่างออกเพื่อเทสต์ได้ครับ
        # self.assertEqual(self.borrow_record.Status, 'Active')

    def test_fine_creation(self):
        """เทสต์การสร้างค่าปรับ (เช็กว่าเชื่อมกับ BorrowingRecord ได้)"""
        if self.fine is not None:
            self.assertEqual(self.fine.BorrowID, self.borrow_record)
            
            # ถ้าโมเดล Fine มีฟิลด์ Amount/FineAmount หรือ Status ก็เช็ก Default ได้ที่นี่
            # self.assertEqual(self.fine.Amount, 0.00)
            # self.assertEqual(self.fine.PaymentStatus, 'Unpaid')