from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from library_app.models import Member, Book, BorrowTransaction

class TypicalDaySystemTestV5(TestCase):
    """
    ทดสอบ Integration Test ของระบบ Smart Library V5.0
    เน้น Flow: SSID Login -> Admin สแกนยืมที่เคาน์เตอร์ -> Admin รับคืน
    """
    
    @classmethod
    def setUpTestData(cls):
        # 1. จำลองข้อมูล Admin (บรรณารักษ์)
        cls.admin_user = Member.objects.create(
            ssid=90000001,
            full_name='Sarah Librarian',
            email='sarah@library.com',
            phone_number='0801112222',
            is_admin=True
        )
        # รหัสผ่านสำหรับ Admin
        cls.admin_password = 'adminpassword123'
        cls.admin_auth = Member.objects.create(member=cls.admin_user)
        cls.admin_auth.set_password(cls.admin_password)
        cls.admin_auth.save()

        # 2. จำลองข้อมูล Member (สมาชิกทั่วไป)
        cls.member_user = Member.objects.create(
            ssid=10000001,
            full_name='Alex Member',
            email='alex@example.com',
            phone_number='0809998888',
            is_admin=False
        )

        # 3. จำลองข้อมูลหนังสือ
        cls.book = Book.objects.create(
            book_id=80000001,
            title='Python for Data Science',
            author='John Doe',
            category='Technology',
            status='Available'
        )

    def setUp(self):
        self.admin_client = Client()
        self.member_client = Client()

    def test_v5_typical_day_workflow(self):
        """
        จำลองเหตุการณ์จริง: Admin ล็อกอิน -> สแกนยืมหนังสือให้ Alex -> Alex คืนหนังสือ
        """
        
        # ==========================================
        # SCENE 1: Admin ล็อกอินเข้าระบบด้วย SSID
        # ==========================================
        # 1.1 Sarah เข้าหน้าแรก (/) และกรอก SSID ของตัวเอง
        response = self.admin_client.post('/', {'ssid': '90000001'})
        
        # ระบบต้อง Redirect ไปหน้า /auth/ เพราะรู้ว่าเป็น Admin
        self.assertRedirects(response, '/auth/')
        
        # 1.2 Sarah กรอกรหัสผ่านที่หน้า /auth/
        response = self.admin_client.post('/auth/', {'password': self.admin_password})
        
        # ถ้ารหัสถูก ต้อง Redirect ไปหน้า Dashboard
        self.assertRedirects(response, '/dashboard/')

        # ==========================================
        # SCENE 2: สมาชิกมายืมหนังสือที่เคาน์เตอร์
        # ==========================================
        # 2.1 Alex หยิบหนังสือมาที่เคาน์เตอร์พร้อมบอก SSID
        borrow_data = {
            'ssid': '10000001',
            'book_id': '80000001',
            'duration': 7,
            'unit': 'days'
        }
        response = self.admin_client.post('/borrow/', data=borrow_data)
        
        # ยืมสำเร็จ ระบบควร Redirect กลับมาหน้า /borrow/
        self.assertRedirects(response, '/borrow/')

        # 2.2 ตรวจสอบใน Database ว่าสถานะการยืมเป็น ACTIVE
        tx = BorrowTransaction.objects.get(member=self.member_user, book=self.book)
        self.assertEqual(tx.status, 'ACTIVE')

        # ==========================================
        # SCENE 3: การตรวจสอบประวัติการยืม (Member View)
        # ==========================================
        # 3.1 Alex กลับบ้าน ลองเข้าเว็บด้วย SSID ตัวเอง
        response = self.member_client.post('/', {'ssid': '10000001'})
        
        # ระบบต้องพา Alex ไปหน้า Member Home
        self.assertRedirects(response, '/member/home/')
        
        # 3.2 ในหน้าประวัติ Alex ต้องเห็นหนังสือ
        response = self.member_client.get('/member/history/')
        self.assertContains(response, 'Python for Data Science')

        # ==========================================
        # SCENE 4: คืนหนังสือที่เคาน์เตอร์ (Admin View)
        # ==========================================
        # 4.1 ผ่านไป 3 วัน Alex นำหนังสือมาคืน Sarah เข้าหน้า /record/
        response = self.admin_client.get('/record/?ssid=10000001')
        self.assertContains(response, tx.tx_id) 

        # 4.2 Sarah กดปุ่ม Return บันทึกการรับคืน
        return_url = reverse('process_return', args=[tx.tx_id]) 
        response = self.admin_client.post(return_url)

        # 4.3 ตรวจสอบความถูกต้องหลังรับคืน
        tx.refresh_from_db()
        
        # สถานะการยืมต้องเป็น RETURNED
        self.assertEqual(tx.status, 'RETURNED')
        self.assertIsNotNone(tx.returned_at)