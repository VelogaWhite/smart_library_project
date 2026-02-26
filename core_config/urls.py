from django.contrib import admin
from django.urls import path , include
from library_app import views  # <-- Import views จากแอป library_app มาโดยตรง

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    
    # เพิ่มบรรทัดนี้สำหรับหน้าสมัครสมาชิก
    path('register/', views.register, name='register'),
    
    # --- เพิ่มบรรทัดนี้ เพื่อให้หน้าแรก (/) ชี้ไปที่หน้าค้นหาหนังสือ ---
    path('', views.search_books, name='home'),
    
    # --- เส้นทางทั้งหมดของระบบห้องสมุด ---\n    
    # Module 3: ค้นหาหนังสือและแสดงผล
    path('search/', views.search_books, name='search_books'),
    
    # Module 4: ยืมหนังสือ
    path('borrow/<int:book_id>/', views.borrow_book, name='borrow_book'),
    
    # Module 5: รับคืนหนังสือ
    path('return/<int:borrow_id>/', views.return_book, name='return_book'),
   
    # Module 6: แดชบอร์ดยืมหนังสือ
    path('librarian/borrow/', views.librarian_borrow_dashboard, name='librarian_borrow_dashboard'),
    
    # Module 7: แดชบอร์ดรรับคืนหนังสือ
    path('librarian/return/', views.librarian_return_dashboard, name='librarian_return_dashboard'),
]