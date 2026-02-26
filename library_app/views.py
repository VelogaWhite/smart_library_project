from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Book, BorrowingRecord, Fine, User, Category
from django.db.models import Q
from .forms import MemberRegistrationForm

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

# --- Module 4: ยืมหนังสือ (Smart Borrowing Logic - REWORKED: ส่งคำร้อง) ---
@login_required 
def borrow_book(request, book_id):
    # อนุญาตให้ Member เท่านั้นกดส่งคำร้องได้
    if request.user.Role == 'Librarian':
        messages.error(request, 'บรรณารักษ์ไม่สามารถยืมหนังสือผ่านหน้านี้ได้')
        return redirect('search_books')

    book = get_object_or_404(Book, id=book_id)
    
    # Logic: จะยืมได้ก็ต่อเมื่อมีสต็อกเหลือ
    if book.AvailableCopies > 0:
        # ป้องกันการกดส่งคำร้องซ้ำ (เช็กว่ามี Pending หรือ Active อยู่ไหม)
        already_requested = BorrowingRecord.objects.filter(
            UserID=request.user, 
            BookID=book, 
            Status__in=['Pending', 'Active']
        ).exists()

        if already_requested:
            messages.warning(request, f'คุณได้ส่งคำร้อง หรือกำลังยืมหนังสือ "{book.Title}" อยู่แล้ว')
        else:
            # 1. บันทึกคำร้อง (Status = 'Pending', ยังไม่มี DueDate)
            BorrowingRecord.objects.create(
                UserID=request.user, 
                BookID=book,
                Status='Pending' 
            )
            
            # 2. ตัดสต็อกหนังสือเพื่อจองไว้ก่อน
            book.AvailableCopies -= 1
            book.save()
            messages.success(request, f'ส่งคำร้องขอยืม "{book.Title}" สำเร็จ กรุณารอการอนุมัติ')
    else:
        messages.error(request, f'ขออภัย "{book.Title}" หมดสต็อกชั่วคราว')

    return redirect('search_books')

# ============================================================
# --- Module 6: หน้าแดชบอร์ดการยืมหนังสือ (REWORKED) ---
# ============================================================
@login_required
def librarian_borrow_dashboard(request):
    if request.user.Role != 'Librarian':
        messages.error(request, 'Access denied. Librarian accounts only.')
        return redirect('search_books')

    # ดึงรายการคำร้องที่รออนุมัติ (Pending)
    pending_requests = BorrowingRecord.objects.filter(
        Status='Pending'
    ).select_related('UserID', 'BookID').order_by('BorrowDate')

    # ดึงประวัติการยืมที่กำลังดำเนินการอยู่ (Active)
    recent_borrows  = BorrowingRecord.objects.filter(
        Status='Active'
    ).select_related('UserID', 'BookID').order_by('-BorrowDate')[:20]

    now = timezone.now()
    for record in recent_borrows:
        record.is_overdue = record.DueDate and record.DueDate < now

    context = {
        'pending_requests': pending_requests,
        'recent_borrows':  recent_borrows,
        'total_pending':   pending_requests.count(),
        'total_active':    BorrowingRecord.objects.filter(Status='Active').count(),
    }
    return render(request, 'library_app/librarian_borrow_dashboard.html', context)

# --- Module 6.1: อนุมัติคำร้อง (Approve) ---
@login_required
def approve_borrow(request, borrow_id):
    if request.user.Role != 'Librarian':
        return redirect('search_books')
        
    if request.method == 'POST':
        record = get_object_or_404(BorrowingRecord, id=borrow_id, Status='Pending')
        
        # เปลี่ยนสถานะเป็น Active และกำหนดวันคืน (สมมติ 7 วัน)
        record.Status = 'Active'
        record.DueDate = timezone.now() + timedelta(days=7)
        # ควรอัปเดต BorrowDate เป็นเวลาที่อนุมัติจริงด้วย
        record.BorrowDate = timezone.now()
        record.save()
        
        messages.success(request, f'✅ อนุมัติคำร้องขอยืม "{record.BookID.Title}" ของ {record.UserID.username} เรียบร้อย')
        
    return redirect('librarian_borrow_dashboard')

# --- Module 6.2: ปฏิเสธคำร้อง (Reject) ---
@login_required
def reject_borrow(request, borrow_id):
    if request.user.Role != 'Librarian':
        return redirect('search_books')
        
    if request.method == 'POST':
        record = get_object_or_404(BorrowingRecord, id=borrow_id, Status='Pending')
        
        # เปลี่ยนสถานะเป็น Rejected
        record.Status = 'Rejected'
        record.save()
        
        # คืนสต็อกหนังสือที่จองไว้
        book = record.BookID
        book.AvailableCopies += 1
        book.save()
        
        messages.warning(request, f'❌ ปฏิเสธคำร้องขอยืม "{record.BookID.Title}" และคืนสต็อกแล้ว')
        
    return redirect('librarian_borrow_dashboard')

# =============================================================
# --- Module 7: หน้าแดชบอร์ดการรับคืนหนังสือ ---
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

# --- Module 5: รับคืนหนังสือ (สำหรับปุ่มทั่วไป) ---
@login_required 
def return_book(request, borrow_id):
    # ฟังก์ชันนี้เก็บไว้รองรับ URL เดิม ถ้าไม่ใช้ลบออกได้ เพราะ logic ไปอยู่ใน dashboard แล้ว
    if request.user.Role != 'Librarian':
        return redirect('search_books')
        
    record = get_object_or_404(BorrowingRecord, id=borrow_id)
    if record.Status != 'Returned':
        record.ReturnDate = timezone.now()
        record.Status = 'Returned'
        record.save()
        
        book = record.BookID
        book.AvailableCopies += 1
        book.save()
    return redirect('librarian_return_dashboard')

# --- Module 8: สมัครสมาชิก (Register) ---
def register(request):
    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.Role = 'Member'  
            user.save()
            messages.success(request, 'Account created successfully! You can now login.')
            return redirect('login') 
    else:
        form = MemberRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})

# เพิ่มหนังสือใหม่
@login_required
def add_book(request):
    if request.method == 'POST' and request.user.Role == 'Librarian':
        category = get_object_or_404(Category, id=request.POST.get('CategoryID'))
        Book.objects.create(
            Title=request.POST.get('Title'),
            CategoryID=category,
            AuthorName=request.POST.get('AuthorName'),
            ISBN=request.POST.get('ISBN'),
            TotalCopies=request.POST.get('TotalCopies'),
            AvailableCopies=request.POST.get('AvailableCopies')
        )
    return redirect('search_books')