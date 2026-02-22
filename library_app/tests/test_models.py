from django.test import TestCase
from library_app.models import Category, Book, User

class LibraryModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # สร้างหมวดหมู่และหนังสือตัวอย่าง
        cls.cat = Category.objects.create(CategoryName="Science")
        cls.book = Book.objects.create(
            Title="Deep Learning", 
            CategoryID=cls.cat, 
            ISBN="999", 
            AvailableCopies=2
        )
        cls.user = User.objects.create_user(username='testuser', Role='Member')

    def test_data_integrity(self):
        """ตรวจสอบว่าข้อมูลถูกบันทึกและดึงออกมาได้ถูกต้อง"""
        self.assertEqual(self.book.Title, "Deep Learning")
        self.assertEqual(self.user.Role, 'Member')