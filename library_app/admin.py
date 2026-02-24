from django.contrib import admin
from .models import Book, Category, BorrowingRecord

admin.site.register(Book)
admin.site.register(Category)
admin.site.register(BorrowingRecord)