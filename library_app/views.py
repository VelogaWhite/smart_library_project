from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Member, Book, BorrowTransaction, AdminAuth
from .forms import MemberRegistrationForm, BookForm


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
                request.session['logged_in_ssid'] = member.ssid # จำลองการ Login
                return redirect('member_profile', ssid=member.ssid)
                
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
                return redirect('index') 
            else:
                messages.error(request, 'รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่')
                
        except AdminAuth.DoesNotExist:
            messages.error(request, 'บัญชี Admin นี้ยังไม่ได้ตั้งรหัสผ่าน! (กรุณาตั้งในหน้า Django Admin)')

    return render(request, 'library_app/auth_admin.html', {'member': member})


def member_profile(request, ssid):
    """ หน้าประวัติการยืมของ Member (/{ssid}/) """
    member = get_object_or_404(Member, ssid=ssid)
    return render(request, 'library_app/user_history.html', {'member': member})

# ==========================================
# Module 2: User Management (Admin Only)
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
# Module 3: Book Management (Admin Only)
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

