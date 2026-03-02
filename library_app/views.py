from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Member, Book, BorrowTransaction, AdminAuth

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