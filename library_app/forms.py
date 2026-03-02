from django import forms
from .models import Member, Book

class MemberRegistrationForm(forms.ModelForm):
    class Meta:
        model = Member
        # ใน V5 เราต้องการแค่ชื่อ อีเมล และเบอร์โทร ส่วน SSID ระบบจะ Gen ให้ตอนบันทึก
        fields = ['full_name', 'email', 'phone_number']

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'isbn', 'category', 'location', 'status']