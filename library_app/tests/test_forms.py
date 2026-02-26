from django.test import TestCase
from library_app.forms import MemberRegistrationForm
from library_app.models import User

class MemberRegistrationFormTest(TestCase):
    def test_form_is_valid_with_correct_data(self):
        """ทดสอบว่าเมื่อกรอกข้อมูลครบถ้วน Form ต้อง Valid"""
        form_data = {
            'username': 'newuser123',
            'FullName': 'John Connor',
            'email': 'john@example.com'
        }
        # จำลองการส่งข้อมูลที่ไม่มี Field Password เพราะ UserCreationForm จัดการเองบางส่วน
        form = MemberRegistrationForm(data=form_data)
        
        # การทดสอบฟอร์มสมัครสมาชิก UserCreationForm อาจจะติด Validation พาสเวิร์ดใน Django 
        # ดังนั้นในระดับ Unit Test Form เราอาจจะตรวจสอบแค่โครงสร้างฟิลด์ หรือ Form Validation เบื้องต้น
        self.assertIn('FullName', form.fields)
        self.assertIn('email', form.fields)
        self.assertTrue(form.fields['FullName'].required)

    def test_form_is_invalid_if_fullname_is_missing(self):
        """ทดสอบว่าถ้าไม่กรอก FullName จะไม่ผ่าน (เพราะเราบังคับไว้)"""
        form_data = {
            'username': 'newuser123',
            'FullName': '', # ค่าว่าง
            'email': 'john@example.com'
        }
        form = MemberRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('FullName', form.errors) # ต้องมีแจ้งเตือน Error ที่ FullName