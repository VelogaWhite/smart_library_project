from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Member, Book, BorrowTransaction, AdminAuth
from .forms import MemberRegistrationForm, BookForm
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.core.paginator import Paginator

# ==========================================
# Module 1: SSID-Based Entry
# ==========================================
def index(request):
    """ หน้าแรกของระบบ (/) รับค่า SSID อย่างเดียว """
    if request.method == 'POST':
        ssid_input = request.POST.get('ssid')
        
        try:
            member = Member.objects.get(ssid=ssid_input)
            
            if member.is_admin:
                # ถ้าเป็น Admin ให้ส่งไปหน้ากรอกรหัสผ่าน (เก็บ SSID ลง Session ไว้ชั่วคราว)
                request.session['temp_admin_ssid'] = member.ssid
                return redirect('admin_auth')
            else:
                # ถ้าเป็น Member ให้ส่งไปหน้าโปรไฟล์ตัวเอง
                request.session['ssid'] = member.ssid
                return redirect('member_home')
                
        except Member.DoesNotExist:
            messages.error(request, 'SSID not found. กรุณาลองใหม่อีกครั้ง')
            return redirect('index')

    return render(request, 'library_app/index.html')


def admin_auth(request):
    """ หน้ากรอกรหัสผ่านสำหรับ Admin (Module 1) """
    # ดึง SSID จาก Session ที่เราดักไว้จากหน้า index
    ssid = request.session.get('temp_admin_ssid')
    
    if not ssid:
        # ถ้าไม่มี Session แปลว่าแอบเข้าหน้านี้ตรงๆ ให้เตะกลับไปหน้าแรก
        return redirect('index')

    member = get_object_or_404(Member, ssid=ssid)

    if request.method == 'POST':
        password = request.POST.get('password')
        try:
            # ดึงข้อมูลรหัสผ่านที่เชื่อมกับ Admin คนนี้
            admin_auth_record = member.auth_profile 
            
            if admin_auth_record.check_password(password):
                # ถ้ารหัสถูก -> ลบ temp session และสร้าง session login จริง
                del request.session['temp_admin_ssid']
                request.session['logged_in_admin_ssid'] = member.ssid
                
                # ชั่วคราว: แสดงข้อความแล้วส่งกลับหน้าแรกก่อน (เดี๋ยวเราค่อยเชื่อมไปหน้า /users)
                messages.success(request, f'Welcome back, {member.full_name} (Admin)')
                return redirect('admin_dashboard') 
            else:
                messages.error(request, 'รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่')
                
        except AdminAuth.DoesNotExist:
            messages.error(request, 'บัญชี Admin นี้ยังไม่ได้ตั้งรหัสผ่าน! (กรุณาตั้งในหน้า Django Admin)')

    return render(request, 'library_app/auth_admin.html', {'member': member})

#==========================================
# MODULE 2 : MEMBER PORTAL MODULE 
#==========================================

def member_profile(request, ssid):
    """ หน้าประวัติการยืมของ Member (/{ssid}/) """
    member = get_object_or_404(Member, ssid=ssid)
    return render(request, 'library_app/user_history.html', {'member': member})


def member_home(request):

    ssid = request.session.get("ssid")

    if not ssid:
        return redirect("index")

    member = Member.objects.get(ssid=ssid)

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

    ssid = request.session.get("ssid")

    if not ssid:
        return redirect("index")

    member = Member.objects.get(ssid=ssid)

    transactions = BorrowTransaction.objects.filter(member=member)

    return render(request, "library_app/member/history.html", {
        "transactions": transactions
    })

def logout_view(request):
    request.session.pop("ssid", None)
    return redirect('index')

# ==========================================
# Module 3: User Management (Admin Only)
# ==========================================
def manage_users(request):
    """ หน้าแสดงรายชื่อและค้นหาสมาชิก """
    if 'logged_in_admin_ssid' not in request.session:
        return redirect('index') # ถ้าไม่ใช่ Admin ให้เตะกลับหน้าแรก

    query = request.GET.get('q', '')
    if query:
        # ค้นหาด้วย SSID
        members = Member.objects.filter(ssid__icontains=query)
    else:
        members = Member.objects.all().order_by('-created_at')

    return render(request, 'library_app/users/list.html', {'members': members, 'query': query})

def create_user(request):
    """ หน้าเพิ่มสมาชิกใหม่ (พร้อม Gen SSID) """
    if 'logged_in_admin_ssid' not in request.session:
        return redirect('index')

    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST)
        if form.is_valid():
            new_member = form.save(commit=False)
            
            # Logic: สร้าง SSID อัตโนมัติ (เอาเลขล่าสุดของ Member ปกติ + 1)
            # เพิ่ม .filter(is_admin=False) เพื่อไม่ให้ไปยุ่งกับเลข 9000xxxx ของ Admin
            last_member = Member.objects.filter(is_admin=False).order_by('ssid').last()
            
            if last_member:
                new_member.ssid = last_member.ssid + 1
            else:
                new_member.ssid = 10000001 # ถ้ายังไม่มี Member ทั่วไปเลย ให้เริ่มที่เลขนี้
                
            new_member.save()
            messages.success(request, f'สร้างสมาชิกสำเร็จ! SSID ของเขาคือ {new_member.ssid}')
            return redirect('manage_users')
    else:
        form = MemberRegistrationForm()
        
    return render(request, 'library_app/users/form.html', {'form': form, 'action': 'Create'})

def edit_user(request, ssid):
    """ หน้าแก้ไขข้อมูลสมาชิก """
    if 'logged_in_admin_ssid' not in request.session:
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
    if 'logged_in_admin_ssid' not in request.session:
        return redirect('index')

    query = request.GET.get('q', '')
    if query:
        books = Book.objects.filter(title__icontains=query) | Book.objects.filter(book_id__icontains=query)
    else:
        books = Book.objects.all().order_by('-book_id')

    return render(request, 'library_app/manage/book_list.html', {'books': books, 'query': query})

def create_book(request):
    """ หน้าเพิ่มหนังสือใหม่ (พร้อม Gen BookID) """
    if 'logged_in_admin_ssid' not in request.session:
        return redirect('index')

    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            new_book = form.save(commit=False)
            
            # Logic: สร้าง BookID อัตโนมัติ (เป็นเลขล้วน)
            last_book = Book.objects.order_by('book_id').last()
            if last_book:
                new_book.book_id = last_book.book_id + 1
            else:
                new_book.book_id = 10001 # เริ่มต้นที่รหัส 10001
                
            new_book.save()
            messages.success(request, f'เพิ่มหนังสือสำเร็จ! รหัสหนังสือคือ {new_book.book_id}')
            return redirect('manage_books')
    else:
        form = BookForm()
        
    return render(request, 'library_app/manage/book_form.html', {'form': form, 'action': 'Add'})

def edit_book(request, book_id):
    """ หน้าแก้ไขข้อมูลหนังสือ """
    if 'logged_in_admin_ssid' not in request.session:
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
    """ ลบหนังสือ (ห้ามลบถ้ากำลังถูกยืมอยู่) """
    if 'logged_in_admin_ssid' not in request.session:
        return redirect('index')

    book = get_object_or_404(Book, book_id=book_id)
    
    # เช็คว่ามีรายการยืมที่ยัง ACTIVE อยู่หรือไม่
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
    """ หน้าทำรายการยืมด้วยการสแกน SSID และ BookID """
    if 'logged_in_admin_ssid' not in request.session:
        return redirect('index')

    if request.method == 'POST':
        ssid_input = request.POST.get('ssid')
        book_id_input = request.POST.get('book_id')
        duration_days = int(request.POST.get('duration', 7)) # ค่าเริ่มต้นให้ยืม 7 วัน

        try:
            member = Member.objects.get(ssid=ssid_input)
            book = Book.objects.get(book_id=book_id_input)

            # 1. ตรวจสอบว่าหนังสือเล่มนี้พร้อมยืมหรือไม่
            if book.status != 'Available':
                messages.error(request, f'❌ หนังสือ "{book.title}" ไม่พร้อมให้ยืม (สถานะปัจจุบัน: {book.status})')
                return redirect('borrow_counter')

            # 2. ตรวจสอบว่าหนังสือเล่มนี้ถูกยืมอยู่และยังไม่ได้คืนหรือไม่ (กันพลาด)
            is_already_borrowed = BorrowTransaction.objects.filter(book=book, status='ACTIVE').exists()
            if is_already_borrowed:
                messages.error(request, f'❌ หนังสือ "{book.title}" กำลังถูกยืมอยู่โดยสมาชิกท่านอื่น!')
                return redirect('borrow_counter')

            # 3. สร้างรายการยืม
            due_date = timezone.now() + timedelta(days=duration_days)
            BorrowTransaction.objects.create(
                member=member,
                book=book,
                due_date=due_date,
                status='ACTIVE'
            )

            messages.success(request, f'✅ ทำรายการสำเร็จ! {member.full_name} ยืม "{book.title}" (กำหนดคืนในอีก {duration_days} วัน)')
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
    """ หน้าค้นหาประวัติการยืมด้วย SSID และแสดงรายการที่ต้องคืน """
    if 'logged_in_admin_ssid' not in request.session:
        return redirect('index')

    query_ssid = request.GET.get('ssid', '')
    member = None
    active_txs = []

    if query_ssid:
        try:
            member = Member.objects.get(ssid=query_ssid)
            # ดึงเฉพาะรายการที่กำลังยืม (ACTIVE) ของสมาชิกคนนี้
            active_txs = member.transactions.filter(status='ACTIVE').order_by('start_date')
        except Member.DoesNotExist:
            messages.error(request, '⚠️ ไม่พบรหัสสมาชิก (SSID) นี้ในระบบ')

    return render(request, 'library_app/borrow/record.html', {
        'member': member, 
        'active_txs': active_txs, 
        'query_ssid': query_ssid
    })

def process_return(request, tx_id):
    """ Logic ประมวลผลการรับคืนและคิดค่าปรับ (เรียกเมื่อกดปุ่ม Return) """
    if 'logged_in_admin_ssid' not in request.session:
        return redirect('index')

    tx = get_object_or_404(BorrowTransaction, tx_id=tx_id)
    
    if tx.status == 'ACTIVE':
        tx.returned_at = timezone.now()
        tx.status = 'RETURNED'
        
        # คำนวณค่าปรับ (สมมติคิดวันละ 10 บาทหากเกิน Due Date)
        if tx.returned_at > tx.due_date:
            overdue_days = (tx.returned_at - tx.due_date).days
            if overdue_days > 0:
                tx.fine_amount = overdue_days * 10.00
                
        tx.save()
        
        # สร้างข้อความแจ้งเตือน (ถ้ามีค่าปรับให้โชว์เป็นสีแดง)
        if tx.fine_amount > 0:
            messages.error(request, f'⚠️ รับคืน "{tx.book.title}" แล้ว (มีค่าปรับ {tx.fine_amount} บาท!)')
        else:
            messages.success(request, f'✅ รับคืน "{tx.book.title}" เรียบร้อยแล้ว')
            
    # ทำเสร็จแล้วเตะกลับไปที่หน้าค้นหาพร้อมส่ง SSID เดิมไปด้วย เพื่อให้เห็นรายการที่เหลือ
    return redirect(f"/record/?ssid={tx.member.ssid}")

# ==========================================
# Module 7: Transaction History
# ==========================================
def transaction_history(request):
    """ หน้าแสดงประวัติธุรกรรมทั้งหมด (ดูได้เฉพาะ Admin) """
    if 'logged_in_admin_ssid' not in request.session:
        return redirect('index')

    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    # ดึงรายการทั้งหมด เรียงจากใหม่ไปเก่า
    txs = BorrowTransaction.objects.all().order_by('-start_date')

    if query:
        # ค้นหาได้ทั้ง SSID ของคนยืม, Book ID และชื่อหนังสือ
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
    """ หน้าหลักของ Settings (แสดงข้อมูลเบื้องต้น) """
    if 'logged_in_admin_ssid' not in request.session:
        return redirect('index')
    
    admin = Member.objects.get(ssid=request.session['logged_in_admin_ssid'])
    return render(request, 'library_app/admin/settings.html', {'admin': admin})

def change_password(request):
    """ Logic สำหรับการเปลี่ยนรหัสผ่าน """
    if 'logged_in_admin_ssid' not in request.session:
        return redirect('index')

    if request.method == 'POST':
        current_pw = request.POST.get('current_password')
        new_pw = request.POST.get('new_password')
        confirm_pw = request.POST.get('confirm_password')
        
        admin = Member.objects.get(ssid=request.session['logged_in_admin_ssid'])
        
        # 1. เช็ครหัสผ่านเดิม (สมมติว่าตอนนี้เรายังไม่ได้ Hash รหัสผ่าน)
        if admin.password != current_pw:
            messages.error(request, '❌ Current password is incorrect.')
        # 2. เช็คว่ารหัสใหม่ตรงกันไหม
        elif new_pw != confirm_pw:
            messages.error(request, '❌ New passwords do not match.')
        # 3. ผ่านเงื่อนไข บันทึกรหัสใหม่
        else:
            admin.password = new_pw
            admin.save()
            messages.success(request, '✅ Password updated successfully!')
            return redirect('admin_settings')

    return redirect('admin_settings')

# ==========================================
# Module 9: Admin Dashboard (สถิติภาพรวม)
# ==========================================
def admin_dashboard(request):
    """ หน้า Dashboard สรุปสถิติและแจ้งเตือนหนังสือค้างส่ง """
    if 'logged_in_admin_ssid' not in request.session:
        return redirect('index')

    # --- คำนวณ Stats Cards 4 กล่อง ---
    total_members = Member.objects.filter(is_admin=False).count()
    total_books   = Book.objects.count()
    active_borrows  = BorrowTransaction.objects.filter(status='ACTIVE').count()
    overdue_count   = BorrowTransaction.objects.filter(status='OVERDUE').count()

    # --- ดึง Overdue Transactions พร้อมข้อมูลสมาชิก (select_related เพื่อกัน N+1) ---
    overdue_transactions = (
        BorrowTransaction.objects
        .filter(status='OVERDUE')
        .select_related('member', 'book')
        .order_by('due_date')   # เรียงจากวันที่เกินนานที่สุดก่อน
    )

    context = {
        'total_members':        total_members,
        'total_books':          total_books,
        'active_borrows':       active_borrows,
        'overdue_count':        overdue_count,
        'overdue_transactions': overdue_transactions,
    }

    return render(request, 'library_app/admin/dashboard.html', context)