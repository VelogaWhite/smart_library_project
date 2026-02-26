from django.test import TestCase
from library_app.models import User, Category, Book, BorrowingRecord, Fine

class LibraryModelsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 1. สร้างหมวดหมู่ (Category)
        cls.category = Category.objects.create(CategoryName='Computer Science')
        
        # 2. สร้างหนังสือ (Book)
        cls.book = Book.objects.create(
            Title='Python 101',
            CategoryID=cls.category,
            AuthorName='John Doe',
            ISBN='1234567890',
            TotalCopies=5,
            AvailableCopies=5
        )
        
        # 3. สร้างผู้ใช้งาน (User)
        cls.member_user = User.objects.create_user(
            username='somchai',
            password='password123',
            FullName='Somchai Jaidee'
        )
        
        # 4. สร้างประวัติการยืม (BorrowingRecord)
        cls.borrow_record = BorrowingRecord.objects.create(
            UserID=cls.member_user,
            BookID=cls.book,
            Status='Pending' # ทดสอบสถานะใหม่ของระบบ
        )

        # 5. สร้างข้อมูลค่าปรับ (Fine)
        cls.fine = Fine.objects.create(
            BorrowID=cls.borrow_record,
            FineAmount=10.00,
            Status='Unpaid'
        )

    def test_category_str(self):
        self.assertEqual(str(self.category), 'Computer Science')

    def test_book_default_values_and_str(self):
        default_book = Book.objects.create(Title='Unknown Journey', CategoryID=self.category, ISBN='000')
        self.assertEqual(default_book.AuthorName, 'Unknown')
        self.assertEqual(default_book.TotalCopies, 1)
        self.assertEqual(str(self.book), 'Python 101')

    def test_user_default_role(self):
        self.assertEqual(self.member_user.Role, 'Member')

    def test_borrowing_record_relationships(self):
        self.assertEqual(self.borrow_record.UserID.username, 'somchai')
        self.assertEqual(self.borrow_record.BookID.Title, 'Python 101')
        self.assertEqual(self.borrow_record.Status, 'Pending')

    def test_fine_relationships_and_values(self):
        self.assertEqual(self.fine.BorrowID, self.borrow_record)
        self.assertEqual(self.fine.FineAmount, 10.00)