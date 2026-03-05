from django.test import TestCase
from library_app.forms import MemberRegistrationForm, BookForm

class MemberRegistrationFormTest(TestCase):
    def test_form_is_valid_with_correct_data(self):
        """ทดสอบว่าเมื่อกรอกข้อมูล V5.0 ครบถ้วน Form ต้อง Valid"""
        form_data = {
            'full_name': 'John Connor',
            'email': 'john@example.com',
            'phone_number': '0812345678'
        }
        form = MemberRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_is_invalid_if_fullname_is_missing(self):
        """ทดสอบว่าถ้าไม่กรอก full_name จะไม่ผ่าน"""
        form_data = {
            'full_name': '', # ค่าว่าง
            'email': 'john@example.com',
            'phone_number': '0812345678'
        }
        form = MemberRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('full_name', form.errors)

class BookFormTest(TestCase):
    def test_book_form_valid(self):
        """ทดสอบการสร้างฟอร์มหนังสือใหม่"""
        form_data = {
            'title': 'Django Testing',
            'author': 'Test Author',
            'isbn': '1234567890',
            'category': 'Programming',
            'location': 'A1',
            'status': 'Available'
        }
        form = BookForm(data=form_data)
        self.assertTrue(form.is_valid())