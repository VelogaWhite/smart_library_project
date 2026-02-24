from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from .models import Book, BorrowingRecord
from django.db.models import Q

# --- Module 3: ค้นหาหนังสือและแสดงผล ---
def search_books(request):
    books = Book.objects.select_related('CategoryID').all()
    query = request.GET.get('q')

    if query:
        books = books.filter(
            Q(Title__icontains=query) |
            Q(ISBN__icontains=query)
        )

    context = {
        'books': books,
        'query': query
    }

    return render(request, 'library_app/search.html', context)

# --- Module 4: ยืมหนังสือ (Smart Borrowing Logic) ---
@login_required # บังคับว่าต้อง Login ก่อนถึงจะยืมได้
def borrow_book(request, book_id):
    # ดึงข้อมูลหนังสือขึ้นมา ถ้าไม่เจอให้แสดง 404
    book = get_object_or_404(Book, id=book_id)
    
    # Logic: จะยืมได้ก็ต่อเมื่อมีสต็อกเหลือ
    if book.AvailableCopies > 0:
        # 1. บันทึกประวัติการยืม (Insert ลงตาราง BorrowingRecord)
        BorrowingRecord.objects.create(
            UserID=request.user, 
            BookID=book,
            DueDate=timezone.now() + timedelta(days=7), # สมมติว่าให้ยืมได้ 7 วัน
            Status='Active' # สถานะกำลังยืม
        )
        
        # 2. ตัดสต็อกหนังสือ (Atomicity)
        book.AvailableCopies -= 1
        book.save()

    # ยืมเสร็จ (หรือยืมไม่ได้เพราะของหมด) ให้เด้งกลับไปหน้าค้นหา
    return redirect('search_books')

# --- Module 5: รับคืนหนังสือ (Return & Fine Logic) ---
@login_required # ในอนาคตอาจจะเพิ่มว่าต้องเป็นบรรณารักษ์เท่านั้น (user.Role == 'Librarian')
def return_book(request, borrow_id):
    # ดึงข้อมูลประวัติการยืม
    record = get_object_or_404(BorrowingRecord, id=borrow_id)
    
    # Logic: ต้องเป็นรายการที่ยังไม่ได้คืน ถึงจะทำรายการได้
    if record.Status != 'Returned':
        # 1. บันทึกเวลาที่คืนจริง และอัปเดตสถานะ
        record.ReturnDate = timezone.now()
        record.Status = 'Returned'
        record.save()
        
        # 2. คืนสต็อกหนังสือให้ระบบ
        book = record.BookID
        book.AvailableCopies += 1
        book.save()
        
        # (ส่วนของการคิดค่าปรับ Fine Logic แบบละเอียด จะเพิ่มได้ที่ตรงนี้ในอนาคต)

    return redirect('search_books')