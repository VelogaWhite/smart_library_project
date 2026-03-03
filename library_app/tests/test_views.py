from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from library_app.models import Member, Book, BorrowTransaction


class MemberPortalViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        """
        ใช้ setUpTestData เพื่อสร้างข้อมูลครั้งเดียวสำหรับทุกเทสต์
        """

        # ==========================
        # สร้างสมาชิก 2 คน
        # ==========================
        cls.member_a = Member.objects.create(
            ssid=10000001,
            full_name="Member A",
            email="a@test.com",
            phone_number="0811111111",
            is_admin=False
        )

        cls.member_b = Member.objects.create(
            ssid=10000002,
            full_name="Member B",
            email="b@test.com",
            phone_number="0822222222",
            is_admin=False
        )

        # ==========================
        # สร้างหนังสือ 2 เล่ม
        # ==========================
        cls.book_1 = Book.objects.create(
            book_id=2001,
            title="Django for Beginners",
            author="William",
            isbn="1234567890",
            category="Technology",
            location="A1",
            status="Available"
        )

        cls.book_2 = Book.objects.create(
            book_id=2002,
            title="Python Advanced",
            author="John",
            isbn="0987654321",
            category="Technology",
            location="A2",
            status="Maintenance"
        )

        now = timezone.now()

        # ==========================
        # Transaction ของ Member A (ACTIVE)
        # ==========================
        cls.tx_a = BorrowTransaction.objects.create(
            member=cls.member_a,
            book=cls.book_1,
            due_date=now + timedelta(days=5),
            returned_at=None,
            fine_amount=0,
            status="ACTIVE"
        )

        # ==========================
        # Transaction ของ Member B (OVERDUE)
        # ==========================
        cls.tx_b = BorrowTransaction.objects.create(
            member=cls.member_b,
            book=cls.book_2,
            due_date=now - timedelta(days=2),
            returned_at=None,
            fine_amount=50,
            status="OVERDUE"
        )

    # ==========================================
    # 🔐 Access Control Tests
    # ==========================================

    def test_member_home_requires_login(self):
        """
        ถ้าไม่มี session ssid ต้อง redirect ไปหน้า /
        """
        response = self.client.get("/member/home/")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/")

    def test_member_history_requires_login(self):
        """
        ถ้าไม่มี session ssid ต้อง redirect ไปหน้า /
        """
        response = self.client.get("/member/history/")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/")

    # ==========================================
    # 📚 Book Visibility Tests
    # ==========================================

    def test_member_can_view_all_books(self):
        """
        สมาชิกที่ login แล้วต้องเห็นหนังสือทั้งหมดในระบบ
        """
        session = self.client.session
        session["ssid"] = self.member_a.ssid
        session.save()

        response = self.client.get("/member/home/")
        self.assertEqual(response.status_code, 200)

        books = response.context["book_list"]
        self.assertEqual(books.count(), 2)

    def test_search_by_title(self):
        """
        ทดสอบค้นหาหนังสือด้วย title__icontains
        """
        session = self.client.session
        session["ssid"] = self.member_a.ssid
        session.save()

        response = self.client.get("/member/home/?q=Django")
        books = response.context["book_list"]

        self.assertEqual(books.count(), 1)
        self.assertEqual(books.first().title, "Django for Beginners")

    def test_search_by_category(self):
        """
        ทดสอบค้นหาหนังสือด้วย category__icontains
        """
        session = self.client.session
        session["ssid"] = self.member_a.ssid
        session.save()

        response = self.client.get("/member/home/?q=Technology")
        books = response.context["book_list"]

        self.assertEqual(books.count(), 2)

    # ==========================================
    # 📖 Borrow Transaction Isolation
    # ==========================================

    def test_member_sees_only_own_transactions(self):
        """
        Member A ต้องไม่เห็น transaction ของ Member B เด็ดขาด
        """
        session = self.client.session
        session["ssid"] = self.member_a.ssid
        session.save()

        response = self.client.get("/member/history/")
        transactions = response.context["transactions"]

        self.assertEqual(transactions.count(), 1)
        self.assertEqual(transactions.first().member, self.member_a)

    # ==========================================
    # ⏳ Overdue Status Display
    # ==========================================

    def test_overdue_status_displayed_correctly(self):
        """
        ตรวจสอบว่า status=OVERDUE ถูกส่งไป template ตรงตาม DB
        (Member Portal ไม่คำนวณใหม่)
        """
        session = self.client.session
        session["ssid"] = self.member_b.ssid
        session.save()

        response = self.client.get("/member/history/")
        transactions = response.context["transactions"]

        self.assertEqual(transactions.count(), 1)
        self.assertEqual(transactions.first().status, "OVERDUE")

    # ==========================================
    # 🎨 Template Usage Tests
    # ==========================================

    def test_member_home_uses_correct_template(self):
        """
        หน้า Member Home ต้องใช้ template member/home.html
        """
        session = self.client.session
        session["ssid"] = self.member_a.ssid
        session.save()

        response = self.client.get("/member/home/")

        self.assertTemplateUsed(response, "library_app/member/home.html")