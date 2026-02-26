from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import User

class MemberRegistrationForm(UserCreationForm):
    # เพิ่มฟิลด์ FullName เข้าไปในฟอร์มสมัคร
    FullName = forms.CharField(max_length=255, required=True, help_text='Enter your full name')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('FullName', 'email',)