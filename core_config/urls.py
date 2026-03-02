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

    # --- Module 3: Book Management ---
    path('manage/', views.manage_books, name='manage_books'),
    path('manage/create/', views.create_book, name='create_book'),
    path('manage/edit/<int:book_id>/', views.edit_book, name='edit_book'),
    path('manage/delete/<int:book_id>/', views.delete_book, name='delete_book'),

    # --- Module 4: Borrow Counter ---
    path('borrow/', views.borrow_counter, name='borrow_counter'),

    # --- Module 5: Return Processing ---
    path('record/', views.return_counter, name='return_counter'),
    path('record/<int:tx_id>/process/', views.process_return, name='process_return'),
]