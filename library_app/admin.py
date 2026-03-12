from django.contrib import admin
from .models import Member, Book, BorrowTransaction

# ลงทะเบียน Models เข้าไปในหน้าต่าง Admin ของ Django
admin.site.register(Member)
admin.site.register(Book)
admin.site.register(BorrowTransaction)