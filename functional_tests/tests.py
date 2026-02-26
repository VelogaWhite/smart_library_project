from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from library_app.models import Book, Category, BorrowingRecord
from datetime import timedelta
from django.utils import timezone

User = get_user_model()

class TypicalDaySystemTest(TestCase):
    def setUp(self):
        # 1. เตรียมข้อมูลพื้นฐาน
        self.category = Category.objects.create(CategoryName="Technology")
        
        self.book = Book.objects.create(
            Title="Python for Beginners",
            CategoryID=self.category,
            AuthorName="John Doe",
            ISBN="123456789",
            TotalCopies=5,
            AvailableCopies=5
        )

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

        self.sarah_client = Client()
        self.alex_client = Client()

    def test_a_typical_day_using_the_system(self):
        """
        ทดสอบ Integrated System Story: A Typical Day Using the System (REWORKED)
        """
        # ==========================================
        # SCENE 1: Sarah เข้าสู่ระบบและอัปเดตหนังสือ
        # ==========================================
        self.sarah_client.login(username='sarah_lib', password='password123')
        
        self.sarah_client.post(reverse('add_book'), {
            'Title': 'Django Web Framework',
            'CategoryID': self.category.id,
            'AuthorName': 'Jane Smith',
            'ISBN': '987654321',
            'TotalCopies': 3,
            'AvailableCopies': 3
        })
        self.assertEqual(Book.objects.count(), 2)

        # ==========================================
        # SCENE 2: Alex ค้นหาหนังสือ
        # ==========================================
        self.alex_client.login(username='alex_mem', password='password123')
        
        response = self.alex_client.get(reverse('search_books'), {'q': 'Django'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django Web Framework')

        # ==========================================
        # SCENE 3: Alex ส่งคำร้องขอยืมหนังสือ (เปลี่ยนจากยืมได้ทันที)
        # ==========================================
        django_book = Book.objects.get(Title='Django Web Framework')
        
        # Alex กดยืมหนังสือ (ระบบใหม่คือส่งคำร้อง)
        self.alex_client.get(reverse('borrow_book', args=[django_book.id]))
        
        django_book.refresh_from_db()
        self.assertEqual(django_book.AvailableCopies, 2) # สต็อกต้องลดลง 1 (เพื่อจอง)
        
        # เช็กว่าคำร้องเป็น 'Pending' (ตรงนี้แหละที่เคยพัง เพราะมันไปเช็กหา Active)
        borrow_record = BorrowingRecord.objects.get(UserID=self.alex, BookID=django_book)
        self.assertEqual(borrow_record.Status, 'Pending')

        # ==========================================
        # SCENE 3.5: Sarah กดอนุมัติคำร้องบน Dashboard (NEW SCENE)
        # ==========================================
        # Sarah เห็นคำร้อง และกดอนุมัติ (ยิง POST ไปยังหน้า approve_borrow)
        self.sarah_client.post(reverse('approve_borrow', args=[borrow_record.id]))
        
        borrow_record.refresh_from_db()
        self.assertEqual(borrow_record.Status, 'Active') # อนุมัติแล้ว สถานะต้องเปลี่ยนเป็น Active
        self.assertIsNotNone(borrow_record.DueDate)

        # ==========================================
        # SCENE 4: คืนหนังสือ
        # ==========================================
        # Sarah กดรับคืนหนังสือ (ผ่าน Dashboard ของบรรณารักษ์)
        self.sarah_client.post(reverse('librarian_return_dashboard'), {'borrow_id': borrow_record.id})
        
        django_book.refresh_from_db()
        borrow_record.refresh_from_db()
        
        # สต็อกต้องกลับมาเป็น 3 เหมือนเดิม และสถานะเป็น Returned
        self.assertEqual(django_book.AvailableCopies, 3)
        self.assertEqual(borrow_record.Status, 'Returned')