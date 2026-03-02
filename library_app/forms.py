from django import forms
from .models import Member

class MemberRegistrationForm(forms.ModelForm):
    class Meta:
        model = Member
        # ใน V5 เราต้องการแค่ชื่อ อีเมล และเบอร์โทร ส่วน SSID ระบบจะ Gen ให้ตอนบันทึก
        fields = ['full_name', 'email', 'phone_number']