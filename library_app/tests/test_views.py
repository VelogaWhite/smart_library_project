from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from library_app.models import User, Category, Book, BorrowingRecord

class BaseViewTest(TestCase):
    """
    คลาสจำลองข้อมูลพื้นฐานสำหรับให้ทุก Test Case เรียกใช้งาน
    """
    @classmethod
    def setUpTestData(cls):
        # สร้าง User
        cls.member = User.objects.create_user(username='member1', password='pw', Role='Member', FullName='Alex Member')
        cls.librarian = User.objects.create_user(username='lib1', password='pw', Role='Librarian', FullName='Sarah Lib')
        
        # สร้าง Category & Book
        cls.category = Category.objects.create(CategoryName='Science')
        cls.book_avail = Book.objects.create(Title='Physics 101', CategoryID=cls.category, ISBN='111', AvailableCopies=2)
        cls.book_unavail = Book.objects.create(Title='Chemistry 101', CategoryID=cls.category, ISBN='222', AvailableCopies=0)

    def setUp(self):
        self.member_client = Client()
        self.member_client.force_login(self.member)
        
        self.lib_client = Client()
        self.lib_client.force_login(self.librarian)

# ==========================================
# 1. เทสต์ฝั่งสมาชิก (Member)
# ==========================================
class MemberViewsTest(BaseViewTest):
    def test_search_books_view(self):
        response = self.member_client.get(reverse('search_books'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'library_app/search.html')
        self.assertIn('books', response.context)

    def test_member_can_request_borrow(self):
        """
        REWORKED: สมาชิกกดยืมหนังสือ ต้องเปลี่ยนเป็น 'Pending' และตัดสต็อกชั่วคราว
        """
        response = self.member_client.get(reverse('borrow_book', args=[self.book_avail.id]))
        
        self.book_avail.refresh_from_db()
        # เช็ก 1: สต็อกต้องลดลง 1 (เพื่อจองของไว้)
        self.assertEqual(self.book_avail.AvailableCopies, 1)
        
        # เช็ก 2: สถานะตารางยืมเป็น Pending และยังไม่มี DueDate
        record = BorrowingRecord.objects.get(UserID=self.member, BookID=self.book_avail)
        self.assertEqual(record.Status, 'Pending')
        self.assertIsNone(record.DueDate)
        
        self.assertRedirects(response, reverse('search_books'))

# ==========================================
# 2. เทสต์ฝั่งบรรณารักษ์ (Librarian)
# ==========================================
class LibrarianViewsTest(BaseViewTest):
    def setUp(self):
        super().setUp()
        # จำลองว่า Member ส่งคำร้องมาก่อนแล้ว 1 รายการ
        self.book_avail.AvailableCopies -= 1
        self.book_avail.save()
        self.pending_req = BorrowingRecord.objects.create(
            UserID=self.member, BookID=self.book_avail, Status='Pending'
        )

    def test_dashboard_access_control(self):
        """Member ห้ามเข้าหน้า Dashboard"""
        response = self.member_client.get(reverse('librarian_borrow_dashboard'))
        self.assertRedirects(response, reverse('search_books'))

    def test_librarian_can_approve_request(self):
        """
        REWORKED: บรรณารักษ์กดอนุมัติ -> สถานะเปลี่ยนเป็น 'Active' และเพิ่มวันคืน (DueDate)
        """
        # สมมติว่าสร้าง URL pattern ชื่อ approve_borrow ไว้รับ POST
        approve_url = reverse('approve_borrow', args=[self.pending_req.id])
        response = self.lib_client.post(approve_url)
        
        self.pending_req.refresh_from_db()
        self.assertEqual(self.pending_req.Status, 'Active')
        self.assertIsNotNone(self.pending_req.DueDate) # ถูกกำหนดวันคืน
        self.assertRedirects(response, reverse('librarian_borrow_dashboard'))

    def test_librarian_can_reject_request(self):
        """
        REWORKED: บรรณารักษ์กดปฏิเสธ -> สถานะเป็น 'Rejected' และได้สต็อกคืน
        """
        before_copies = self.book_avail.AvailableCopies
        reject_url = reverse('reject_borrow', args=[self.pending_req.id])
        response = self.lib_client.post(reject_url)
        
        self.pending_req.refresh_from_db()
        self.book_avail.refresh_from_db()
        
        self.assertEqual(self.pending_req.Status, 'Rejected')
        self.assertEqual(self.book_avail.AvailableCopies, before_copies + 1) # คืนสต็อกที่จองไว้
        self.assertRedirects(response, reverse('librarian_borrow_dashboard'))

    def test_librarian_can_process_return(self):
        """เทสต์ระบบคืนหนังสือของบรรณารักษ์"""
        # จำลองเป็น Active ก่อน
        self.pending_req.Status = 'Active'
        self.pending_req.DueDate = timezone.now() + timedelta(days=7)
        self.pending_req.save()

        before_copies = self.book_avail.AvailableCopies
        return_url = reverse('return_book', args=[self.pending_req.id])
        
        # สมมติบรรณารักษ์กดรับคืน
        response = self.lib_client.post(return_url)
        
        self.pending_req.refresh_from_db()
        self.book_avail.refresh_from_db()
        
        self.assertEqual(self.pending_req.Status, 'Returned')
        self.assertIsNotNone(self.pending_req.ReturnDate)
        self.assertEqual(self.book_avail.AvailableCopies, before_copies + 1) # คืนสต็อก