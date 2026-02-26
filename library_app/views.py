from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Book, BorrowingRecord , Fine ,User
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
# --- Module 6: หน้าแดชบอร์ดการยืมหนังสือ (สำหรับ บรรณารักษ์เท่านั้น) ---
# ============================================================
@login_required
def librarian_borrow_dashboard(request):
    # ตรวจสอบว่าผู้ใช้งานมีสิทธิ์เป็นบรรณารักษ์ (Librarian) หรือไม่
    # หากไม่มีสิทธิ์ ให้แสดงข้อความแจ้งเตือนและส่งกลับไปที่หน้าค้นหาหนังสือ
    if request.user.Role != 'Librarian':
        messages.error(request, 'Access denied. Librarian accounts only.')
        return redirect('search_books')

    # ส่วนจัดการข้อมูลเมื่อบรรณารักษ์กดยืนยันการยืมหนังสือ
    if request.method == 'POST':
        # รับค่ารหัสสมาชิก รหัสหนังสือ และจำนวนวันที่จะให้ยืมจากฟอร์ม (ค่าเริ่มต้นคือ 7 วัน)
        member_id = request.POST.get('member_id')
        book_id   = request.POST.get('book_id')
        due_days  = int(request.POST.get('due_days', 7))

        # ดึงข้อมูลสมาชิกและหนังสือจากฐานข้อมูล หากไม่พบจะแสดงหน้า 404
        member = get_object_or_404(User, id=member_id)
        book   = get_object_or_404(Book, id=book_id)

        # ตรวจสอบว่าหนังสือเล่มนี้มีจำนวนคงเหลือให้ยืมหรือไม่
        if book.AvailableCopies > 0:
            # ตรวจสอบว่าสมาชิกคนนี้กำลังยืมหนังสือเล่มเดียวกันอยู่แล้วหรือไม่ ป้องกันการยืมซ้ำ
            already_borrowed = BorrowingRecord.objects.filter(
                UserID=member, BookID=book, Status='Active'
            ).exists()

            if not already_borrowed:
                # สร้างประวัติการยืมใหม่ พร้อมตั้งค่าสถานะเป็น 'Active' และกำหนดวันคืน
                BorrowingRecord.objects.create(
                    UserID=member,
                    BookID=book,
                    DueDate=timezone.now() + timedelta(days=due_days),
                    Status='Active'
                )
                # หักจำนวนหนังสือที่พร้อมให้ยืมลง 1 เล่มและบันทึกลงฐานข้อมูล
                book.AvailableCopies -= 1
                book.save()
                messages.success(request, f'✅ "{book.Title}" successfully borrowed by {member.FullName or member.username}.')
            else:
                # กรณีที่สมาชิกกำลังยืมหนังสือเล่มนี้อยู่แล้ว
                messages.warning(request, f'⚠️ {member.FullName or member.username} already has an active borrow for "{book.Title}".')
        else:
            # กรณีที่ไม่มีหนังสือเล่มนี้เหลือให้ยืมแล้ว
            messages.error(request, f'❌ "{book.Title}" has no available copies right now.')

        # ทำงานเสร็จแล้วให้รีเฟรชกลับมาที่หน้าเดิม
        return redirect('librarian_borrow_dashboard')

    # ส่วนการเตรียมข้อมูลสำหรับแสดงผลบนหน้าเว็บ (GET Request)
    # ดึงรายชื่อสมาชิกและหนังสือที่ยังมีให้ยืม เพื่อนำไปแสดงใน Dropdown
    members         = User.objects.filter(Role='Member').order_by('username')
    available_books = Book.objects.filter(AvailableCopies__gt=0).order_by('Title')
    
    # ดึงประวัติการยืมที่กำลังดำเนินการอยู่ (Active) ล่าสุด 20 รายการ
    recent_borrows  = BorrowingRecord.objects.filter(
        Status='Active'
    ).select_related('UserID', 'BookID').order_by('-BorrowDate')[:20]

    now = timezone.now()
    # ตรวจสอบว่ารายการยืมแต่ละอันเลยกำหนดคืน (Overdue) แล้วหรือยัง
    for record in recent_borrows:
        record.is_overdue = record.DueDate and record.DueDate < now

    # รวบรวมข้อมูลทั้งหมดส่งไปยัง Template
    context = {
        'members':         members,
        'available_books': available_books,
        'recent_borrows':  recent_borrows,
        'total_active':    BorrowingRecord.objects.filter(Status='Active').count(),
    }
    return render(request, 'library_app/librarian_borrow_dashboard.html', context)


# =============================================================
# --- Module 7: หน้าแดชบอร์ดการรับคืนหนังสือ (สำหรับ บรรณารักษ์เท่านั้น) ---
# =============================================================
@login_required
def librarian_return_dashboard(request):
    # ตรวจสอบสิทธิ์ว่าผู้ใช้งานเป็นบรรณารักษ์หรือไม่
    if request.user.Role != 'Librarian':
        messages.error(request, 'Access denied. Librarian accounts only.')
        return redirect('search_books')

    # ส่วนจัดการข้อมูลเมื่อบรรณารักษ์กดยืนยันการคืนหนังสือ
    if request.method == 'POST':
        # รับค่ารหัสการยืมเพื่อระบุว่าจะคืนรายการไหน
        borrow_id = request.POST.get('borrow_id')
        record    = get_object_or_404(BorrowingRecord, id=borrow_id)

        # ป้องกันการคืนซ้ำซ้อน ตรวจสอบว่าสถานะต้องยังไม่เป็น 'Returned'
        if record.Status != 'Returned':
            # บันทึกวันที่คืนจริง และอัปเดตสถานะเป็น 'Returned'
            record.ReturnDate = timezone.now()
            record.Status     = 'Returned'
            record.save()

            # เพิ่มจำนวนหนังสือในสต็อกกลับเข้ามา 1 เล่ม
            book = record.BookID
            book.AvailableCopies += 1
            book.save()

            # ตรวจสอบว่ามีการส่งคืนล่าช้ากว่ากำหนดหรือไม่
            if record.DueDate and record.ReturnDate > record.DueDate:
                # คำนวณจำนวนวันที่เกินกำหนด และคิดค่าปรับวันละ 5.00 บาท
                overdue_days = (record.ReturnDate - record.DueDate).days
                fine_amount  = overdue_days * 5.00
                
                # สร้างข้อมูลบิลค่าปรับสถานะ 'Unpaid' (ยังไม่ชำระ)
                Fine.objects.create(
                    BorrowID=record,
                    FineAmount=fine_amount,
                    Status='Unpaid'
                )
                messages.warning(request, f'⚠️ "{book.Title}" returned {overdue_days} day(s) late. Fine of ฿{fine_amount:.2f} has been recorded.')
            else:
                # คืนตรงเวลา
                messages.success(request, f'✅ "{book.Title}" has been returned successfully.')
        else:
            # กรณีที่รายการนี้ถูกคืนไปเรียบร้อยแล้ว
            messages.info(request, 'This record has already been marked as returned.')

        # รีเฟรชกลับมาที่หน้าเดิม
        return redirect('librarian_return_dashboard')

    # ส่วนการเตรียมข้อมูลสำหรับแสดงผลบนหน้าเว็บ (GET Request)
    now = timezone.now()
    
    # ดึงข้อมูลการยืมทั้งหมดที่ยังไม่คืน (Active) เรียงตามวันครบกำหนด
    active_records = BorrowingRecord.objects.filter(
        Status='Active'
    ).select_related('UserID', 'BookID').order_by('DueDate')

    # ตรวจสอบว่ารายการที่ยังไม่คืนอันไหนเลยกำหนดแล้วบ้าง
    for record in active_records:
        record.is_overdue = record.DueDate and record.DueDate < now

    # ดึงข้อมูลประวัติที่คืนหนังสือเสร็จสิ้นแล้ว ล่าสุด 20 รายการ
    returned_records = BorrowingRecord.objects.filter(
        Status='Returned'
    ).select_related('UserID', 'BookID').order_by('-ReturnDate')[:20]

    # รวบรวมข้อมูลทั้งหมดส่งไปยัง Template
    context = {
        'active_records':   active_records,
        'returned_records': returned_records,
        'active_count':     active_records.count(),
        'overdue_count':    sum(1 for r in active_records if r.is_overdue),
    }
    return render(request, 'library_app/librarian_return_dashboard.html', context)

# --- Module 8: สมัครสมาชิก (Register) ---
def register(request):
    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.Role = 'Member'  # บังคับให้คนที่สมัครใหม่เป็น Member เสมอ
            user.save()
            messages.success(request, 'Account created successfully! You can now login.')
            return redirect('login') # สมัครเสร็จให้เด้งไปหน้า login
    else:
        form = MemberRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})