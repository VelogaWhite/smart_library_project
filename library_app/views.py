from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Book, BorrowingRecord, Fine, User, Category, BookCopy
from .forms import MemberRegistrationForm # ตรวจสอบว่าชื่อ Form ตรงกับที่มีอยู่

# --- Module 3: ค้นหาหนังสือ ---
def search_books(request):
    # ใช้ prefetch_related('bookcopy_set') เพื่อลด Query ตอนเรียกใช้ @property ในหน้า HTML
    books = Book.objects.select_related('CategoryID').prefetch_related('bookcopy_set').all()
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

# --- Module 4: ส่งคำร้องขอยืมหนังสือ (Member) ---
@login_required 
def borrow_book(request, book_id):
    if request.user.Role == 'Librarian':
        messages.error(request, 'บรรณารักษ์ไม่สามารถยืมหนังสือผ่านหน้านี้ได้')
        return redirect('search_books')

    book = get_object_or_404(Book, id=book_id)
    
    # เช็กสต็อกผ่าน @property (available_copies) ที่นับจาก BookCopy สถานะ 'Available'
    if book.available_copies > 0:
        already_requested = BorrowingRecord.objects.filter(
            UserID=request.user, 
            BookID=book, 
            Status__in=['Pending', 'Active']
        ).exists()

        if already_requested:
            messages.warning(request, f'คุณได้ส่งคำร้อง หรือกำลังยืม "{book.Title}" อยู่แล้ว')
        else:
            # สร้างคำร้อง (Status='Pending') โดยยังไม่ระบุ BookCopyID 
            # (จะระบุตอน Librarian กด Approve)
            BorrowingRecord.objects.create(
                UserID=request.user, 
                BookID=book,
                Status='Pending' 
            )
            messages.success(request, f'ส่งคำร้องขอยืม "{book.Title}" สำเร็จ กรุณารอรับหนังสือที่เคาน์เตอร์')
    else:
        messages.error(request, f'ขออภัย "{book.Title}" หมดสต็อกชั่วคราว')

    return redirect('search_books')

# --- Module 6: จัดการคำร้อง (Librarian) ---
@login_required
def librarian_borrow_dashboard(request):
    if request.user.Role != 'Librarian':
        return redirect('search_books')
    
    pending_records = BorrowingRecord.objects.filter(Status='Pending').select_related('UserID', 'BookID')
    return render(request, 'library_app/librarian_borrow_dashboard.html', {'records': pending_records})

@login_required
def approve_borrow(request, borrow_id):
    """
    ขั้นตอนนี้คือการผูกเล่มหนังสือจริง (BookCopy) เข้ากับคำร้อง
    """
    if request.user.Role != 'Librarian':
        return redirect('search_books')

    record = get_object_or_404(BorrowingRecord, id=borrow_id, Status='Pending')
    
    # ค้นหาเล่มที่ว่างเล่มแรก (First Available Copy)
    copy = BookCopy.objects.filter(BookID=record.BookID, Status='Available').first()
    
    if copy:
        # อัปเดตสถานะเล่มหนังสือ
        copy.Status = 'Borrowed'
        copy.save()
        
        # อัปเดต Record การยืม
        record.BookCopyID = copy
        record.Status = 'Active'
        record.BorrowDate = timezone.now()
        record.DueDate = timezone.now() + timedelta(days=7) # ยืมได้ 7 วัน
        record.save()
        
        messages.success(request, f'อนุมัติการยืมเล่มบาร์โค้ด {copy.Barcode} สำเร็จ')
    else:
        messages.error(request, 'ไม่พบเล่มหนังสือที่ว่างในระบบ')
        
    return redirect('librarian_borrow_dashboard')

@login_required
def reject_borrow(request, borrow_id):
    if request.user.Role != 'Librarian':
        return redirect('search_books')
        
    record = get_object_or_404(BorrowingRecord, id=borrow_id, Status='Pending')
    record.Status = 'Rejected'
    record.save()
    messages.warning(request, f'ปฏิเสธคำร้องของ {record.UserID.username} เรียบร้อย')
    return redirect('librarian_borrow_dashboard')

# --- Module 7: รับคืนหนังสือ ---
@login_required
def return_book(request, borrow_id):
    if request.user.Role != 'Librarian':
        return redirect('search_books')

    record = get_object_or_404(BorrowingRecord, id=borrow_id, Status='Active')
    
    # 1. เปลี่ยนสถานะเล่มหนังสือ (BookCopy) ให้กลับมาว่าง
    if record.BookCopyID:
        copy = record.BookCopyID
        copy.Status = 'Available'
        copy.save()

    # 2. อัปเดต Record การคืน
    record.ReturnDate = timezone.now()
    record.Status = 'Returned'
    record.save()

# 3. จัดการค่าปรับ (ถ้ามี)
    if record.is_overdue():
        days_late = (record.ReturnDate - record.DueDate).days
        amount = days_late * 10 # วันละ 10 บาท
        # เปลี่ยน BorrowingID เป็น BorrowID และ Amount เป็น FineAmount
        Fine.objects.create(BorrowID=record, FineAmount=amount) 
        messages.warning(request, f'คืนหนังสือล่าช้า {days_late} วัน มีค่าปรับ {amount} บาท')
    else:
        messages.success(request, 'คืนหนังสือเรียบร้อย')

    return redirect('search_books')

# --- Module 7: แดชบอร์ดรับคืนหนังสือ (Librarian) ---
@login_required
def librarian_return_dashboard(request):
    # ป้องกันไม่ให้ Member เข้าหน้านี้
    if request.user.Role != 'Librarian':
        messages.error(request, 'เฉพาะบรรณารักษ์เท่านั้นที่สามารถเข้าถึงหน้านี้ได้')
        return redirect('search_books')
        
    # ดึงประวัติการคืนหนังสือทั้งหมด (เรียงจากคืนล่าสุดไปเก่าสุด)
    return_records = BorrowingRecord.objects.filter(Status='Returned').order_by('-ReturnDate')
    
    context = {
        'return_records': return_records
    }
    return render(request, 'library_app/librarian_return_dashboard.html', context)

# --- Module 8: ระบบจัดการข้อมูลพื้นฐาน ---
def register(request):
    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.Role = 'Member'  
            user.save()
            messages.success(request, 'สร้างบัญชีสำเร็จ! เข้าสู่ระบบได้เลย')
            return redirect('login') 
    else:
        form = MemberRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def add_book(request):
    if request.user.Role != 'Librarian':
        return redirect('search_books')

    if request.method == 'POST':
        category = get_object_or_404(Category, id=request.POST.get('CategoryID'))
        
        # สร้าง Book (หัวเรื่อง)
        new_book = Book.objects.create(
            Title=request.POST.get('Title'),
            CategoryID=category,
            AuthorName=request.POST.get('AuthorName'),
            ISBN=request.POST.get('ISBN')
        )

        # สร้าง BookCopy (เล่มจริง) ตามจำนวน TotalCopies ที่ส่งมาจาก Form
        num_copies = int(request.POST.get('TotalCopies', 0))
        for i in range(num_copies):
            BookCopy.objects.create(
                BookID=new_book,
                Barcode=f"{new_book.ISBN}-{i+1}",
                Status='Available'
            )
            
        messages.success(request, f'เพิ่มหนังสือและสร้างเล่มใหม่ {num_copies} เล่มเรียบร้อย')
        return redirect('search_books')

    return render(request, 'library_app/add_book.html', {'categories': Category.objects.all()})