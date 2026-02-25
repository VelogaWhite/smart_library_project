from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Book, BorrowingRecord , Fine ,User
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

# ============================================================
# --- Module 6: LIBRARIAN BORROW DASHBOARD (Librarian Only) ---
# ============================================================
@login_required
def librarian_borrow_dashboard(request):
    if request.user.Role != 'Librarian':
        messages.error(request, 'Access denied. Librarian accounts only.')
        return redirect('search_books')

    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        book_id   = request.POST.get('book_id')
        due_days  = int(request.POST.get('due_days', 7))

        member = get_object_or_404(User, id=member_id)
        book   = get_object_or_404(Book, id=book_id)

        if book.AvailableCopies > 0:
            already_borrowed = BorrowingRecord.objects.filter(
                UserID=member, BookID=book, Status='Active'
            ).exists()

            if not already_borrowed:
                BorrowingRecord.objects.create(
                    UserID=member,
                    BookID=book,
                    DueDate=timezone.now() + timedelta(days=due_days),
                    Status='Active'
                )
                book.AvailableCopies -= 1
                book.save()
                messages.success(request, f'✅ "{book.Title}" successfully borrowed by {member.FullName or member.username}.')
            else:
                messages.warning(request, f'⚠️ {member.FullName or member.username} already has an active borrow for "{book.Title}".')
        else:
            messages.error(request, f'❌ "{book.Title}" has no available copies right now.')

        return redirect('librarian_borrow_dashboard')

    members         = User.objects.filter(Role='Member').order_by('username')
    available_books = Book.objects.filter(AvailableCopies__gt=0).order_by('Title')
    recent_borrows  = BorrowingRecord.objects.filter(
        Status='Active'
    ).select_related('UserID', 'BookID').order_by('-BorrowDate')[:20]

    now = timezone.now()
    for record in recent_borrows:
        record.is_overdue = record.DueDate and record.DueDate < now

    context = {
        'members':         members,
        'available_books': available_books,
        'recent_borrows':  recent_borrows,
        'total_active':    BorrowingRecord.objects.filter(Status='Active').count(),
    }
    return render(request, 'library_app/librarian_borrow_dashboard.html', context)


# =============================================================
# --- Module 7: LIBRARIAN RETURN DASHBOARD (Librarian Only) ---
# =============================================================
@login_required
def librarian_return_dashboard(request):
    if request.user.Role != 'Librarian':
        messages.error(request, 'Access denied. Librarian accounts only.')
        return redirect('search_books')

    if request.method == 'POST':
        borrow_id = request.POST.get('borrow_id')
        record    = get_object_or_404(BorrowingRecord, id=borrow_id)

        if record.Status != 'Returned':
            record.ReturnDate = timezone.now()
            record.Status     = 'Returned'
            record.save()

            book = record.BookID
            book.AvailableCopies += 1
            book.save()

            if record.DueDate and record.ReturnDate > record.DueDate:
                overdue_days = (record.ReturnDate - record.DueDate).days
                fine_amount  = overdue_days * 5.00
                Fine.objects.create(
                    BorrowID=record,
                    FineAmount=fine_amount,
                    Status='Unpaid'
                )
                messages.warning(request, f'⚠️ "{book.Title}" returned {overdue_days} day(s) late. Fine of ฿{fine_amount:.2f} has been recorded.')
            else:
                messages.success(request, f'✅ "{book.Title}" has been returned successfully.')
        else:
            messages.info(request, 'This record has already been marked as returned.')

        return redirect('librarian_return_dashboard')

    now = timezone.now()
    active_records = BorrowingRecord.objects.filter(
        Status='Active'
    ).select_related('UserID', 'BookID').order_by('DueDate')

    for record in active_records:
        record.is_overdue = record.DueDate and record.DueDate < now

    returned_records = BorrowingRecord.objects.filter(
        Status='Returned'
    ).select_related('UserID', 'BookID').order_by('-ReturnDate')[:20]

    context = {
        'active_records':   active_records,
        'returned_records': returned_records,
        'active_count':     active_records.count(),
        'overdue_count':    sum(1 for r in active_records if r.is_overdue),
    }
    return render(request, 'library_app/librarian_return_dashboard.html', context)