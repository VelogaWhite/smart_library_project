from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Member, Book, BorrowTransaction
from .forms import MemberRegistrationForm, BookForm
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.core.paginator import Paginator

# ==========================================
# Module 1: Unified Login & Authentication
# ==========================================
def index(request):
    """ หน้า Login รวม (รับทั้ง SSID และ Password ในหน้าเดียว) """
    # หากล็อกอินอยู่แล้ว ให้ข้ามหน้า Login ไปเลย
    if 'member_id' in request.session:
        if request.session.get('is_admin'):
            return redirect('admin_dashboard')
        else:
            return redirect('member_home')

    if request.method == 'POST':
        ssid_input = request.POST.get('ssid')
        password_input = request.POST.get('password')

        try:
            # 1. ค้นหาผู้ใช้ด้วย SSID
            member = Member.objects.get(ssid=ssid_input)
            
            # 2. ตรวจสอบรหัสผ่าน (ใช้ check_password จาก Schema 5.1)
            if member.check_password(password_input):
                # 3. บันทึกข้อมูลลง Session แบบมาตรฐานเดียวกัน
                request.session['member_id'] = member.ssid
                request.session['is_admin'] = member.is_admin
                request.session['full_name'] = member.full_name
                
                # 4. แยกเส้นทางตาม Role
                if member.is_admin:
                    messages.success(request, f'ยินดีต้อนรับ บรรณารักษ์ {member.full_name}')
                    return redirect('admin_dashboard')
                else:
                    messages.success(request, f'ยินดีต้อนรับ {member.full_name}')
                    return redirect('member_home')
            else:
                messages.error(request, 'รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง')
                
        except Member.DoesNotExist:
            messages.error(request, 'ไม่พบรหัสสมาชิกนี้ในระบบ')
        except ValueError:
            messages.error(request, 'รหัสสมาชิกต้องเป็นตัวเลขเท่านั้น')

    # หมายเหตุ: อย่าลืมแก้โค้ด HTML ใน login.html (หรือ index.html) ให้มีช่องกรอก password ด้วย
    return render(request, 'library_app/login.html')

def logout_view(request):
    """ ล้าง Session ทั้งหมดตอนออกจากระบบ """
    request.session.flush()
    messages.info(request, 'ออกจากระบบเรียบร้อยแล้ว')
    return redirect('index')

#==========================================
# MODULE 2 : MEMBER PORTAL MODULE 
#==========================================

def member_profile(request, ssid):
    """ หน้าประวัติการยืมของ Member (/{ssid}/) """
    member = get_object_or_404(Member, ssid=ssid)
    return render(request, 'library_app/user_history.html', {'member': member})

def member_home(request):
    """ หน้าแรกของสมาชิกทั่วไป """
    member_id = request.session.get("member_id")

    if not member_id:
        return redirect("index")

    member = Member.objects.get(ssid=member_id)
    books = Book.objects.all().order_by("book_id")

    query = request.GET.get("q")
    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(category__icontains=query)
        )

    context = {
        "book_list": books,
        "member": member
    }

    return render(request, "library_app/member/home.html", context)

def my_history(request):
    """ หน้าประวัติการยืมส่วนตัวของสมาชิก """
    member_id = request.session.get("member_id")

    if not member_id:
        return redirect("index")

    member = Member.objects.get(ssid=member_id)
    view_tab = request.GET.get('tab', 'active')

    if view_tab == 'history':
        transactions = BorrowTransaction.objects.filter(member=member, status='RETURNED').order_by('-returned_at')
    else:
        transactions = BorrowTransaction.objects.filter(member=member).exclude(status='RETURNED').order_by('due_date')

    return render(request, "library_app/member/history.html", {
        "transactions": transactions,
        "view_tab": view_tab
    })


# ==========================================
# Module 3: User Management (Admin Only)
# ==========================================
def manage_users(request):
    """ หน้าแสดงรายชื่อและค้นหาสมาชิก """
    if not request.session.get('is_admin'):
        return redirect('index')

    query = request.GET.get('q', '')
    if query:
        members = Member.objects.filter(ssid__icontains=query)
    else:
        members = Member.objects.all().order_by('-created_at')

    return render(request, 'library_app/users/list.html', {'members': members, 'query': query})

def create_user(request):
    """ หน้าเพิ่มสมาชิกใหม่ (พร้อม Gen SSID และตั้งรหัสผ่านเริ่มต้น) """
    if not request.session.get('is_admin'):
        return redirect('index')

    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST)
        if form.is_valid():
            new_member = form.save(commit=False)
            
            # Logic: สร้าง SSID อัตโนมัติ (เอาเลขล่าสุดของ Member ปกติ + 1)
            last_member = Member.objects.filter(is_admin=False).order_by('ssid').last()
            
            if last_member:
                new_member.ssid = last_member.ssid + 1
            else:
                new_member.ssid = 10000001
            
            # ตั้งรหัสผ่านเริ่มต้นให้สมาชิกใหม่เป็น "member123"
            new_member.set_password("member123")
                
            new_member.save()
            messages.success(request, f'สร้างสมาชิกสำเร็จ! SSID คือ {new_member.ssid} รหัสผ่านเริ่มต้น: member123')
            return redirect('manage_users')
    else:
        form = MemberRegistrationForm()
        
    return render(request, 'library_app/users/form.html', {'form': form, 'action': 'Create'})

def edit_user(request, ssid):
    """ หน้าแก้ไขข้อมูลสมาชิก """
    if not request.session.get('is_admin'):
        return redirect('index')

    member = get_object_or_404(Member, ssid=ssid)
    
    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, f'อัปเดตข้อมูลของ {member.full_name} สำเร็จ!')
            return redirect('manage_users')
    else:
        form = MemberRegistrationForm(instance=member)
        
    return render(request, 'library_app/users/form.html', {'form': form, 'action': 'Edit', 'member': member})

# ==========================================
# Module 4: Book Management (Admin Only)
# ==========================================
def manage_books(request):
    """ หน้าแสดงรายการหนังสือและค้นหา """
    if not request.session.get('is_admin'):
        return redirect('index')

    query = request.GET.get('q', '')
    if query:
        books = Book.objects.filter(title__icontains=query) | Book.objects.filter(book_id__icontains=query)
    else:
        books = Book.objects.all().order_by('-book_id')

    return render(request, 'library_app/manage/book_list.html', {'books': books, 'query': query})

def create_book(request):
    """ หน้าเพิ่มหนังสือใหม่ """
    if not request.session.get('is_admin'):
        return redirect('index')

    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            new_book = form.save(commit=False)
            
            last_book = Book.objects.order_by('book_id').last()
            if last_book:
                new_book.book_id = last_book.book_id + 1
            else:
                new_book.book_id = 10001
                
            new_book.save()
            messages.success(request, f'เพิ่มหนังสือสำเร็จ! รหัสหนังสือคือ {new_book.book_id}')
            return redirect('manage_books')
    else:
        form = BookForm()
        
    return render(request, 'library_app/manage/book_form.html', {'form': form, 'action': 'Add'})

def edit_book(request, book_id):
    """ หน้าแก้ไขข้อมูลหนังสือ """
    if not request.session.get('is_admin'):
        return redirect('index')

    book = get_object_or_404(Book, book_id=book_id)
    
    if request.method == 'POST':
        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, f'อัปเดตข้อมูลหนังสือ {book.title} สำเร็จ!')
            return redirect('manage_books')
    else:
        form = BookForm(instance=book)
        
    return render(request, 'library_app/manage/book_form.html', {'form': form, 'action': 'Edit', 'book': book})

def delete_book(request, book_id):
    """ ลบหนังสือ """
    if not request.session.get('is_admin'):
        return redirect('index')

    book = get_object_or_404(Book, book_id=book_id)
    active_borrows = book.transactions.filter(status='ACTIVE').exists()
    
    if active_borrows:
        messages.error(request, f'ไม่สามารถลบ "{book.title}" ได้ เนื่องจากหนังสือกำลังถูกยืมอยู่!')
    else:
        book.delete()
        messages.success(request, f'ลบหนังสือ "{book.title}" เรียบร้อยแล้ว')
        
    return redirect('manage_books')

# ==========================================
# Module 5: Borrow Creation (หน้าเคาน์เตอร์ยืม)
# ==========================================
def borrow_counter(request):
    """ หน้าทำรายการยืม """
    if not request.session.get('is_admin'):
        return redirect('index')

    if request.method == 'POST':
        ssid_input = request.POST.get('ssid')
        book_id_input = request.POST.get('book_id')
        duration_days = int(request.POST.get('duration', 7))

        try:
            member = Member.objects.get(ssid=ssid_input)
            book = Book.objects.get(book_id=book_id_input)

            if book.status != 'Available':
                messages.error(request, f'❌ หนังสือ "{book.title}" ไม่พร้อมให้ยืม')
                return redirect('borrow_counter')

            is_already_borrowed = BorrowTransaction.objects.filter(book=book, status='ACTIVE').exists()
            if is_already_borrowed:
                messages.error(request, f'❌ หนังสือ "{book.title}" กำลังถูกยืมอยู่โดยสมาชิกท่านอื่น!')
                return redirect('borrow_counter')

            due_date = timezone.now() + timedelta(days=duration_days)
            BorrowTransaction.objects.create(
                member=member,
                book=book,
                due_date=due_date,
                status='ACTIVE'
            )
            
            # อัปเดตสถานะหนังสือด้วย
            book.status = 'BORROWED'
            book.save()

            messages.success(request, f'✅ ทำรายการสำเร็จ! {member.full_name} ยืม "{book.title}"')
            return redirect('borrow_counter')

        except Member.DoesNotExist:
            messages.error(request, '⚠️ ไม่พบรหัสสมาชิก (SSID) นี้ในระบบ')
        except Book.DoesNotExist:
            messages.error(request, '⚠️ ไม่พบรหัสหนังสือ (Book ID) นี้ในระบบ')
        except ValueError:
            messages.error(request, '⚠️ กรุณากรอกรหัสเป็นตัวเลขเท่านั้น')

    return render(request, 'library_app/borrow/create_tx.html')

# ==========================================
# Module 6: Return Processing (หน้าเคาน์เตอร์รับคืน)
# ==========================================
def return_counter(request):
    """ หน้าค้นหาประวัติการยืมเพื่อคืน """
    if not request.session.get('is_admin'):
        return redirect('index')

    query_ssid = request.GET.get('ssid', '')
    member = None
    active_txs = []

    if query_ssid:
        try:
            member = Member.objects.get(ssid=query_ssid)
            active_txs = member.transactions.filter(status='ACTIVE').order_by('start_date')
        except Member.DoesNotExist:
            messages.error(request, '⚠️ ไม่พบรหัสสมาชิก (SSID) นี้ในระบบ')

    return render(request, 'library_app/borrow/record.html', {
        'member': member, 
        'active_txs': active_txs, 
        'query_ssid': query_ssid
    })

def process_return(request, tx_id):
    """ ประมวลผลการรับคืน """
    if not request.session.get('is_admin'):
        return redirect('index')

    tx = get_object_or_404(BorrowTransaction, tx_id=tx_id)
    
    if tx.status == 'ACTIVE':
        tx.returned_at = timezone.now()
        tx.status = 'RETURNED'
        
        # ปรับสถานะหนังสือกลับเป็น Available
        tx.book.status = 'AVAILABLE'
        tx.book.save()
        
        # คำนวณค่าปรับ
        if tx.returned_at > tx.due_date:
            overdue_days = (tx.returned_at - tx.due_date).days
            if overdue_days > 0:
                tx.fine_amount = overdue_days * 10.00
                
        tx.save()
        
        if tx.fine_amount > 0:
            messages.error(request, f'⚠️ รับคืน "{tx.book.title}" แล้ว (มีค่าปรับ {tx.fine_amount} บาท!)')
        else:
            messages.success(request, f'✅ รับคืน "{tx.book.title}" เรียบร้อยแล้ว')
            
    return redirect(f"/record/?ssid={tx.member.ssid}")

# ==========================================
# Module 7: Transaction History
# ==========================================
def transaction_history(request):
    """ หน้าแสดงประวัติธุรกรรมทั้งหมด """
    if not request.session.get('is_admin'):
        return redirect('index')

    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    txs = BorrowTransaction.objects.all().order_by('-start_date')

    if query:
        txs = txs.filter(
            Q(member__ssid__icontains=query) |
            Q(book__book_id__icontains=query) |
            Q(book__title__icontains=query)
        )
    
    if status_filter:
        txs = txs.filter(status=status_filter)

    return render(request, 'library_app/transaction/list.html', {
        'transactions': txs,
        'query': query,
        'status_filter': status_filter
    })

# ==========================================
# Module 8: Admin Settings (Change Password)
# ==========================================
def admin_settings(request):
    """ หน้าหลักของ Settings """
    if not request.session.get('is_admin'):
        return redirect('index')
    
    admin = Member.objects.get(ssid=request.session['member_id'])
    return render(request, 'library_app/admin/settings.html', {'admin': admin})

def change_password(request):
    """ Logic สำหรับการเปลี่ยนรหัสผ่าน (อัปเดตใช้ check_password / set_password) """
    if not request.session.get('is_admin'):
        return redirect('index')

    if request.method == 'POST':
        current_pw = request.POST.get('current_password')
        new_pw = request.POST.get('new_password')
        confirm_pw = request.POST.get('confirm_password')
        
        admin = Member.objects.get(ssid=request.session['member_id'])
        
        # 1. เช็ครหัสผ่านเดิมผ่านระบบ Hash
        if not admin.check_password(current_pw):
            messages.error(request, '❌ รหัสผ่านปัจจุบันไม่ถูกต้อง')
        # 2. เช็คว่ารหัสใหม่ตรงกันไหม
        elif new_pw != confirm_pw:
            messages.error(request, '❌ รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน')
        # 3. ผ่านเงื่อนไข บันทึกรหัสใหม่
        else:
            admin.set_password(new_pw)
            admin.save()
            messages.success(request, '✅ อัปเดตรหัสผ่านสำเร็จ!')
            return redirect('admin_settings')

    return redirect('admin_settings')

# ==========================================
# Module 9: Admin Dashboard (สถิติภาพรวม)
# ==========================================
def admin_dashboard(request):
    """ หน้า Dashboard """
    if not request.session.get('is_admin'):
        return redirect('index')

    total_members = Member.objects.filter(is_admin=False).count()
    total_books   = Book.objects.count()
    active_borrows  = BorrowTransaction.objects.filter(status='ACTIVE').count()
    overdue_count   = BorrowTransaction.objects.filter(status='OVERDUE').count()

    overdue_transactions = (
        BorrowTransaction.objects
        .filter(status='OVERDUE')
        .select_related('member', 'book')
        .order_by('due_date')
    )

    context = {
        'total_members':        total_members,
        'total_books':          total_books,
        'active_borrows':       active_borrows,
        'overdue_count':        overdue_count,
        'overdue_transactions': overdue_transactions,
    }

    return render(request, 'library_app/admin/dashboard.html', context)