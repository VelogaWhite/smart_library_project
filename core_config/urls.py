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
    
    # --- Module 2: User Management ---
    path('users/', views.manage_users, name='manage_users'),
    path('users/create/', views.create_user, name='create_user'),
    path('users/edit/<int:ssid>/', views.edit_user, name='edit_user'),
]