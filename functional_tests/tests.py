from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

# นำเข้า Models ที่ "คาดว่า" จะถูกสร้างขึ้นใหม่ใน V5.0
# (หมายเหตุ: หากคุณหยกยังไม่ได้แก้ models.py เทสต์นี้จะ Error ซึ่งเป็นเรื่องปกติของ TDD ครับ)
try:
    from library_app.models import Member, Book, BorrowTransaction
except ImportError:
    # ใส่ไว้เผื่อกรณีที่ models.py ยังเป็น V4 อยู่
    pass

class TypicalDaySystemTestV5(TestCase):
    """
    ทดสอบ Integration Test ของระบบ Smart Library V5.0
    เน้น Flow: SSID Login -> Admin สแกนยืมที่เคาน์เตอร์ -> Admin รับคืน
    """
    
    @classmethod
    def setUpTestData(cls):
        # 1. จำลองข้อมูล Admin (บรรณารักษ์)
        cls.admin_user = Member.objects.create(
            ssid='90000001',
            full_name='Sarah Librarian',
            email='sarah@library.com',
            phone_number='0801112222',
            is_admin=True
        )
        # รหัสผ่านสำหรับ Admin (สมมติว่าใน V5 จะมีการเก็บ hashed password สำหรับ admin ต่างหาก 
        # หรืออาจจะเช็คจากฟิลด์เฉพาะ เราจะจำลองการตั้งค่าเบื้องต้นไว้ก่อน)
        cls.admin_password = 'adminpassword123'

        # 2. จำลองข้อมูล Member (สมาชิกทั่วไป)
        cls.member_user = Member.objects.create(
            ssid='10000001',
            full_name='Alex Member',
            email='alex@example.com',
            phone_number='0809998888',
            is_admin=False
        )

        # 3. จำลองข้อมูลหนังสือ (BookID เป็นตัวเลขล้วนตาม V5)
        cls.book = Book.objects.create(
            book_id='80000001',
            title='Python for Data Science',
            author='John Doe',
            category='Technology',
            status='Available'
        )

    def setUp(self):
        # ใช้ Client สองตัวเพื่อจำลองเบราว์เซอร์ของ Admin และ Member แยกกัน
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
        
        # ระบบต้อง Redirect ไปหน้า /auth เพราะรู้ว่าเป็น Admin
        self.assertRedirects(response, '/auth')
        
        # 1.2 Sarah กรอกรหัสผ่านที่หน้า /auth
        response = self.admin_client.post('/auth', {'password': self.admin_password})
        
        # ถ้ารหัสถูก ต้อง Redirect ไปหน้า Dashboard (เช่น /transaction หรือ /borrow)
        # สมมติว่าล็อกอินสำเร็จไปหน้า /borrow
        self.assertRedirects(response, '/borrow')

        # ==========================================
        # SCENE 2: สมาชิกมายืมหนังสือที่เคาน์เตอร์
        # ==========================================
        # 2.1 Alex หยิบหนังสือ (BookID: 80000001) มาที่เคาน์เตอร์พร้อมบอก SSID (10000001)
        # Sarah ใช้ระบบยิงบาร์โค้ดลงฟอร์มในหน้า /borrow
        borrow_data = {
            'ssid': '10000001',
            'book_id': '80000001',
            'duration': 7, # ยืม 7 วัน
            'unit': 'days'
        }
        response = self.admin_client.post('/borrow', data=borrow_data)
        
        # ยืมสำเร็จ ระบบควร Redirect กลับมาหน้า /borrow หรือไปหน้าประวัติ
        self.assertEqual(response.status_code, 302) 

        # 2.2 ตรวจสอบใน Database ว่าสถานะการยืมเป็น ACTIVE
        tx = BorrowTransaction.objects.get(ssid=self.member_user, book_id=self.book)
        self.assertEqual(tx.status, 'ACTIVE')
        
        # ตรวจสอบว่าสถานะหนังสือเปลี่ยนเป็น Borrowed
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, 'Borrowed') # หรือสถานะอื่นๆ ตามที่ออกแบบไว้

        # ==========================================
        # SCENE 3: การตรวจสอบประวัติการยืม (Member View)
        # ==========================================
        # 3.1 Alex กลับบ้าน ลองเข้าเว็บด้วย SSID ตัวเอง
        response = self.member_client.post('/', {'ssid': '10000001'})
        
        # ระบบต้องพา Alex ไปหน้าประวัติส่วนตัวของตัวเองโดยตรง (ไม่มีหน้ากรอกรหัสผ่าน)
        self.assertRedirects(response, '/10000001')
        
        # 3.2 ในหน้าประวัติ Alex ต้องเห็นหนังสือ 'Python for Data Science'
        response = self.member_client.get('/10000001/history')
        self.assertContains(response, 'Python for Data Science')
        self.assertContains(response, 'ACTIVE')

        # ==========================================
        # SCENE 4: คืนหนังสือที่เคาน์เตอร์ (Admin View)
        # ==========================================
        # 4.1 ผ่านไป 3 วัน Alex นำหนังสือมาคืน Sarah เข้าหน้า /record
        # กรอก SSID ของ Alex เพื่อดึงรายการที่กำลังยืม
        response = self.admin_client.get('/record?ssid=10000001')
        self.assertContains(response, tx.tx_id) # ต้องเจอ transaction id นี้

        # 4.2 Sarah กดปุ่ม Return บันทึกการรับคืน
        return_url = reverse('return_transaction', args=[tx.tx_id]) # สมมติชื่อ URL
        response = self.admin_client.post(return_url)

        # 4.3 ตรวจสอบความถูกต้องหลังรับคืน
        tx.refresh_from_db()
        self.book.refresh_from_db()
        
        # สถานะการยืมต้องเป็น RETURNED
        self.assertEqual(tx.status, 'RETURNED')
        self.assertIsNotNone(tx.returned_at) # ต้องมีวันที่บันทึกการคืน
        
        # หนังสือต้องกลับมาพร้อมให้คนอื่นยืม (Available)
        self.assertEqual(self.book.status, 'Available')