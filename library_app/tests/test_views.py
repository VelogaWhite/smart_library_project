from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from library_app.models import User, Category, Book, BorrowingRecord

# ... (เทสต์ SearchBooksViewTest ของเดิมที่ผ่านแล้ว) ...
class SearchBooksViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.member = User.objects.create_user(username='member1', password='pw', Role='Member')
        cls.category = Category.objects.create(CategoryName='Science')
        cls.available_book = Book.objects.create(Title='Physics 101', CategoryID=cls.category, ISBN='111', AvailableCopies=2)
        cls.unavailable_book = Book.objects.create(Title='Chemistry 101', CategoryID=cls.category, ISBN='222', AvailableCopies=0)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.member)

    def test_search_books_uses_correct_template(self):
        response = self.client.get(reverse('search_books'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'library_app/search.html')

    def test_search_books_context_contains_required_data(self):
        response = self.client.get(reverse('search_books'))
        self.assertIn('books', response.context)
        first_book = response.context['books'].first()
        self.assertIsNotNone(first_book.id)

    def test_availability_status_is_calculated_correctly(self):
        response = self.client.get(reverse('search_books'))
        books_in_context = response.context['books']
        physics = books_in_context.get(ISBN='111')
        chemistry = books_in_context.get(ISBN='222')
        self.assertTrue(physics.AvailableCopies > 0)
        self.assertFalse(chemistry.AvailableCopies > 0)

# ==========================================
# TEST: Module 4 (ยืมหนังสือ)
# ==========================================
class BorrowBookViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='borrower', password='pw', Role='Member')
        self.client.force_login(self.user)
        self.category = Category.objects.create(CategoryName='IT')
        self.book = Book.objects.create(Title='Django Basic', CategoryID=self.category, ISBN='333', AvailableCopies=1)

    def test_borrow_book_success_reduces_stock_and_creates_record(self):
        """เทสต์ว่ายืมสำเร็จ สต็อกต้องลดลง และมีประวัติบันทึก"""
        response = self.client.get(reverse('borrow_book', args=[self.book.id]))
        
        # รีเฟรชข้อมูลล่าสุดจาก Database
        self.book.refresh_from_db()
        
        # เช็ก 1: สต็อกต้องลดลงเหลือ 0
        self.assertEqual(self.book.AvailableCopies, 0)
        # เช็ก 2: มีตารางบันทึกการยืมถูกสร้างขึ้นมา 1 รายการ
        self.assertEqual(BorrowingRecord.objects.count(), 1)
        record = BorrowingRecord.objects.first()
        self.assertEqual(record.BookID, self.book)
        self.assertEqual(record.UserID, self.user)
        self.assertEqual(record.Status, 'Active')
        
        # เช็ก 3: ทำรายการเสร็จต้อง Redirect กลับไปหน้าค้นหา
        self.assertRedirects(response, reverse('search_books'))

# ==========================================
# TEST: Module 5 (รับคืนหนังสือ)
# ==========================================
class ReturnBookViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.librarian = User.objects.create_user(username='librarian1', password='pw', Role='Librarian')
        self.client.force_login(self.librarian)
        
        self.category = Category.objects.create(CategoryName='Math')
        # หนังสือเหลือ 0 เล่ม เพราะถูกยืมไปแล้ว
        self.book = Book.objects.create(Title='Calculus', CategoryID=self.category, ISBN='444', AvailableCopies=0)
        
        # จำลองข้อมูลว่ามีการยืมค้างไว้
        self.borrow_record = BorrowingRecord.objects.create(
            UserID=self.librarian,
            BookID=self.book,
            DueDate=timezone.now(),
            Status='Active'
        )

    def test_return_book_success_increases_stock_and_updates_status(self):
        """เทสต์ว่าคืนหนังสือสำเร็จ สต็อกต้องเพิ่ม และประวัติอัปเดตเป็น Returned"""
        response = self.client.get(reverse('return_book', args=[self.borrow_record.id]))
        
        self.book.refresh_from_db()
        self.borrow_record.refresh_from_db()
        
        # เช็ก 1: สต็อกต้องได้คืนมาเป็น 1
        self.assertEqual(self.book.AvailableCopies, 1)
        # เช็ก 2: ประวัติต้องเปลี่ยนเป็น 'Returned' และมีเวลากำกับ
        self.assertEqual(self.borrow_record.Status, 'Returned')
        self.assertIsNotNone(self.borrow_record.ReturnDate)