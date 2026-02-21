from django.shortcuts import render

# TODO: สร้าง Views สำหรับการค้นหาหนังสือ (Module 3)
def search_books(request):
    return render(request, 'library_app/search.html')

# TODO: สร้าง Views สำหรับการยืมหนังสือ (Module 4)
def borrow_book(request, book_id):
    pass

# TODO: สร้าง Views สำหรับบรรณารักษ์ในการรับคืน (Module 5)
def return_book(request, borrow_id):
    pass