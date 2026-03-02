from django.contrib import admin
from django.urls import path
from library_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- Module 1: SSID-Based Entry ---
    path('', views.index, name='index'), # หน้าแรก
    path('auth/', views.admin_auth, name='admin_auth'), # หน้าใส่รหัสผ่าน Admin
    
    # --- Member View ---
    path('<int:ssid>/', views.member_profile, name='member_profile'),
    
    # (Route อื่นๆ สำหรับจัดการระบบ จะคอมเมนต์ไว้ก่อน เดี๋ยวเรามาทยอยเปิดใช้กัน)
    # path('users/', views.manage_users, name='manage_users'),
    # path('manage/', views.manage_books, name='manage_books'),
    # path('borrow/', views.borrow_counter, name='borrow_counter'),
    # path('record/', views.return_counter, name='return_counter'),
]