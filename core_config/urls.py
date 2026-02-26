from django.contrib import admin
from django.urls import path, include
from library_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    
    path('register/', views.register, name='register'),
    path('', views.search_books, name='home'),
    path('add_book/', views.add_book, name='add_book'),
    
    # Module 3: ค้นหาหนังสือและแสดงผล
    path('search/', views.search_books, name='search_books'),
    
    # Module 4: ยืมหนังสือ (ส่งคำร้อง)
    path('borrow/<int:book_id>/', views.borrow_book, name='borrow_book'),
    
    # Module 5: รับคืนหนังสือ
    path('return/<int:borrow_id>/', views.return_book, name='return_book'),
   
    # Module 6: แดชบอร์ดยืมหนังสือ และ ระบบคำร้อง
    path('librarian/borrow/', views.librarian_borrow_dashboard, name='librarian_borrow_dashboard'),
    path('librarian/approve/<int:borrow_id>/', views.approve_borrow, name='approve_borrow'), # เพิ่มใหม่
    path('librarian/reject/<int:borrow_id>/', views.reject_borrow, name='reject_borrow'),    # เพิ่มใหม่
    
    # Module 7: แดชบอร์ดรรับคืนหนังสือ
    path('librarian/return/', views.librarian_return_dashboard, name='librarian_return_dashboard'),
]