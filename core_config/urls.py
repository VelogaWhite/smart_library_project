from django.contrib import admin
from django.urls import path
from library_app import views  # <-- Import views จากแอป library_app มาโดยตรง

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- เส้นทางทั้งหมดของระบบห้องสมุด ---
    
    # Module 3: ค้นหาหนังสือและแสดงผล
    path('search/', views.search_books, name='search_books'),
    
    # Module 4: ยืมหนังสือ
    path('borrow/<int:book_id>/', views.borrow_book, name='borrow_book'),
    
    # Module 5: รับคืนหนังสือ
    path('return/<int:borrow_id>/', views.return_book, name='return_book'),
]