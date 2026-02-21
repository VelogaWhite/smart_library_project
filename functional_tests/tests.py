from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from library_app.models import Book, Category, BorrowingRecord
from datetime import timedelta
from django.utils import timezone

User = get_user_model()

class TypicalDaySystemTest(TestCase):
    def setUp(self):
        # 1. เตรียมข้อมูลพื้นฐาน (Setup Database)
        # สร้างหมวดหมู่
        self.category = Category.objects.create(CategoryName="Technology")
        
        # สร้างหนังสือตั้งต้น
        self.book = Book.objects.create(
            Title="Python for Beginners",
            CategoryID=self.category,
            AuthorName="John Doe",
            ISBN="123456789",
            TotalCopies=5,
            AvailableCopies=5
        )

        # สร้างตัวละครตาม User Story
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

        # จำลองคอมพิวเตอร์ 2 เครื่องที่ Login พร้อมกันตาม User Story
        self.sarah_client = Client()
        self.alex_client = Client()

    def test_a_typical_day_using_the_system(self):
        """
        ทดสอบ Integrated System Story: A Typical Day Using the System
        """
        # ==========================================
        # SCENE 1: Sarah เข้าสู่ระบบและอัปเดตหนังสือ
        # ==========================================
        # "Sarah Login เข้าสู่ระบบจาก Service Desk... Manage Book Collection"
        self.sarah_client.login(username='sarah_lib', password='password123')
        
        # จำลองการที่ Sarah เพิ่มหนังสือเล่มใหม่เข้าระบบ (สมมติว่ายิง POST request ไปที่ url ชื่อ 'add_book')
        # หมายเหตุ: เพื่อนที่ทำ View ต้องสร้าง URL name 'add_book' มารองรับ
        response = self.sarah_client.post(reverse('add_book'), {
            'Title': 'Django Web Framework',
            'CategoryID': self.category.id,
            'AuthorName': 'Jane Smith',
            'ISBN': '987654321',
            'TotalCopies': 3,
            'AvailableCopies': 3
        })
        # ตรวจสอบว่าเพิ่มหนังสือสำเร็จ (มีหนังสือในระบบ 2 เล่มแล้ว)
        self.assertEqual(Book.objects.count(), 2)

        # ==========================================
        # SCENE 2: Alex ค้นหาหนังสือ
        # ==========================================
        # "ในเวลาเดียวกัน Alex Access ระบบจากระยะไกล... เข้าสู่ Member Interface... ใช้ Search Feature"
        self.alex_client.login(username='alex_mem', password='password123')
        
        # Alex ค้นหาคำว่า 'Django'
        response = self.alex_client.get(reverse('search_books'), {'q': 'Django'})
        self.assertEqual(response.status_code, 200)
        
        # ตรวจสอบว่าระบบสะท้อนข้อมูลที่ Sarah เพิ่งอัปเดต (Visible ต่อ Member ทันที)
        self.assertContains(response, 'Django Web Framework')
        self.assertContains(response, 'Available') # Confirm Availability

        # ==========================================
        # SCENE 3: Alex ทำการยืมหนังสือ
        # ==========================================
        # "Initiate Borrow Process ผ่าน System... System จะ Record Transaction และ Update Book Status"
        django_book = Book.objects.get(Title='Django Web Framework')
        
        # Alex กดยืมหนังสือ
        response = self.alex_client.post(reverse('borrow_book', args=[django_book.id]))
        
        # ดึงข้อมูลหนังสือมาเช็คใหม่
        django_book.refresh_from_db()
        
        # ตรวจสอบ Shared Visibility: สต็อกต้องลดลง 1 (จาก 3 เหลือ 2)
        self.assertEqual(django_book.AvailableCopies, 2)
        
        # ตรวจสอบว่ามี Transaction บันทึกไว้จริงๆ
        borrow_record = BorrowingRecord.objects.get(UserID=self.alex, BookID=django_book)
        self.assertIsNotNone(borrow_record)
        self.assertEqual(borrow_record.Status, 'Active')

        # ==========================================
        # SCENE 4: คืนหนังสือ
        # ==========================================
        # "Alex นำหนังสือมาคืน Sarah Process Return ผ่าน System ซึ่งจะ Restore Availability"
        
        # Sarah กดรับคืนหนังสือ (ผ่าน Dashboard ของบรรณารักษ์)
        response = self.sarah_client.post(reverse('return_book', args=[borrow_record.id]))
        
        # ดึงข้อมูลมาเช็คอีกรอบ
        django_book.refresh_from_db()
        borrow_record.refresh_from_db()
        
        # ตรวจสอบว่าสต็อกกลับมาเป็น 3 เหมือนเดิม (Restore Availability)
        self.assertEqual(django_book.AvailableCopies, 3)
        
        # ตรวจสอบว่าสถานะการยืมถูกเปลี่ยนเป็น Returned แล้ว
        self.assertEqual(borrow_record.Status, 'Returned')
        self.assertIsNotNone(borrow_record.ReturnDate)