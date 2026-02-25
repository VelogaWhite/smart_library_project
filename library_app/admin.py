from django.contrib import admin
from .models import Book, Category, BorrowingRecord ,User

admin.site.register(Book)
admin.site.register(Category)
admin.site.register(BorrowingRecord)
admin.site.register(User)   #เพิ่มหน้าต่างในการแก้ไข user