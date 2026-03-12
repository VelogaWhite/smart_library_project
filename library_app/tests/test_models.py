from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from library_app.models import Member, Book, BorrowTransaction

class LibraryModelsTestV5(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 1. สร้าง Member ทั่วไป
        cls.member = Member.objects.create(
            ssid=10000001,
            full_name='Somchai Jaidee',
            email='somchai@test.com',
            phone_number='0811111111',
            is_admin=False
        )
        
        # 2. สร้าง Admin และรหัสผ่าน
        cls.admin = Member.objects.create(
            ssid=90000001,
            full_name='Admin User',
            email='admin@test.com',
            phone_number='0899999999',
            is_admin=True
        )
        cls.admin_auth = Member(member=cls.admin)
        cls.admin_auth.set_password('admin123')
        cls.admin_auth.save()

        # 3. สร้าง Book
        cls.book = Book.objects.create(
            book_id=80000001,
            title='Python 101',
            author='John Doe',
            isbn='1234567890',
            category='Technology',
            location='A1',
            status='Available'
        )

        # 4. สร้าง Borrow Transaction
        cls.tx = BorrowTransaction.objects.create(
            member=cls.member,
            book=cls.book,
            due_date=timezone.now() + timedelta(days=7),
            status='ACTIVE'
        )

    def test_member_str_representation(self):
        self.assertEqual(str(self.member), '[10000001] Somchai Jaidee (Member)')
        self.assertEqual(str(self.admin), '[90000001] Admin User (Admin)')

    def test_book_str_representation(self):
        self.assertEqual(str(self.book), '[80000001] Python 101')

    def test_borrow_transaction_status(self):
        self.assertEqual(self.tx.status, 'ACTIVE')
        self.assertFalse(self.tx.is_overdue) # ยืมวันนี้ กำหนดคืนอีก 7 วัน ต้องยังไม่ overdue

    def test_overdue_property_logic(self):
        # จำลองการแก้ไขให้กำหนดคืนเป็นเมื่อวานนี้
        self.tx.due_date = timezone.now() - timedelta(days=1)
        self.tx.save()
        
        # property is_overdue ต้องกลายเป็น True ทันที
        self.assertTrue(self.tx.is_overdue)