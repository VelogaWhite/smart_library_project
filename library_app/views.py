from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Member, Book, BorrowTransaction
from .forms import MemberRegistrationForm, BookForm
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.core.paginator import Paginator

# Import สำหรับ Data Visualization
import pandas as pd
import plotly.express as px

# ==========================================
# Module 1: Unified Login & Authentication
# ==========================================
def index(request):
    """ หน้า Login รวม (รับทั้ง SSID และ Password ในหน้าเดียว) """
    if 'member_id' in request.session:
        if request.session.get('is_admin'):
            return redirect('admin_dashboard')
        else:
            return redirect('member_home')

    if request.method == 'POST':
        ssid_input = request.POST.get('ssid')
        password_input = request.POST.get('password')

        try:
            member = Member.objects.get(ssid=ssid_input)
            
            if member.check_password(password_input):
                request.session['member_id'] = member.ssid
                request.session['is_admin'] = member.is_admin
                request.session['full_name'] = member.full_name
                
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

    return render(request, 'library_app/login.html')

def logout_view(request):
    request.session.flush()
    messages.info(request, 'ออกจากระบบเรียบร้อยแล้ว')
    return redirect('index')

#==========================================
# MODULE 2 : MEMBER PORTAL MODULE 
#==========================================
def member_profile(request, ssid):
    member = get_object_or_404(Member, ssid=ssid)
    return render(request, 'library_app/user_history.html', {'member': member})

def member_home(request):
    member_id = request.session.get("member_id")
    if not member_id: return redirect("index")

    member = Member.objects.get(ssid=member_id)
    books = Book.objects.all().order_by("book_id")

    query = request.GET.get("q")
    if query:
        books = books.filter(Q(title__icontains=query) | Q(category__icontains=query))

    return render(request, "library_app/member/home.html", {"book_list": books, "member": member})

def my_history(request):
    member_id = request.session.get("member_id")
    if not member_id: return redirect("index")

    member = Member.objects.get(ssid=member_id)
    view_tab = request.GET.get('tab', 'active')

    if view_tab == 'history':
        transactions = BorrowTransaction.objects.filter(member=member, status='RETURNED').order_by('-returned_at')
    else:
        transactions = BorrowTransaction.objects.filter(member=member).exclude(status='RETURNED').order_by('due_date')

    return render(request, "library_app/member/history.html", {"transactions": transactions, "view_tab": view_tab})

# ==========================================
# Module 3: User Management (Admin Only)
# ==========================================
def manage_users(request):
    if not request.session.get('is_admin'): return redirect('index')

    query = request.GET.get('q', '')
    if query:
        members = Member.objects.filter(ssid__icontains=query)
    else:
        members = Member.objects.all().order_by('-created_at')

    return render(request, 'library_app/users/list.html', {'members': members, 'query': query})

def create_user(request):
    if not request.session.get('is_admin'): return redirect('index')

    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST)
        if form.is_valid():
            new_member = form.save(commit=False)
            last_member = Member.objects.filter(is_admin=False).order_by('ssid').last()
            
            new_member.ssid = last_member.ssid + 1 if last_member else 10000001
            new_member.set_password("member123")
            new_member.save()
            messages.success(request, f'สร้างสมาชิกสำเร็จ! SSID คือ {new_member.ssid} รหัสผ่านเริ่มต้น: member123')
            return redirect('manage_users')
    else:
        form = MemberRegistrationForm()
        
    return render(request, 'library_app/users/form.html', {'form': form, 'action': 'Create'})

def edit_user(request, ssid):
    if not request.session.get('is_admin'): return redirect('index')

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
    if not request.session.get('is_admin'): return redirect('index')

    query = request.GET.get('q', '')
    if query:
        books = Book.objects.filter(title__icontains=query) | Book.objects.filter(book_id__icontains=query)
    else:
        books = Book.objects.all().order_by('-book_id')

    return render(request, 'library_app/manage/book_list.html', {'books': books, 'query': query})

def create_book(request):
    if not request.session.get('is_admin'): return redirect('index')

    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            new_book = form.save(commit=False)
            last_book = Book.objects.order_by('book_id').last()
            new_book.book_id = last_book.book_id + 1 if last_book else 10001
            new_book.save()
            messages.success(request, f'เพิ่มหนังสือสำเร็จ! รหัสหนังสือคือ {new_book.book_id}')
            return redirect('manage_books')
    else:
        form = BookForm()
        
    return render(request, 'library_app/manage/book_form.html', {'form': form, 'action': 'Add'})

def edit_book(request, book_id):
    if not request.session.get('is_admin'): return redirect('index')

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
    if not request.session.get('is_admin'): return redirect('index')

    book = get_object_or_404(Book, book_id=book_id)
    if book.transactions.filter(status='ACTIVE').exists():
        messages.error(request, f'ไม่สามารถลบ "{book.title}" ได้ เนื่องจากหนังสือกำลังถูกยืมอยู่!')
    else:
        book.delete()
        messages.success(request, f'ลบหนังสือ "{book.title}" เรียบร้อยแล้ว')
        
    return redirect('manage_books')

# ==========================================
# Module 5: Borrow Creation
# ==========================================
def borrow_counter(request):
    if not request.session.get('is_admin'): return redirect('index')

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

            if BorrowTransaction.objects.filter(book=book, status='ACTIVE').exists():
                messages.error(request, f'❌ หนังสือ "{book.title}" กำลังถูกยืมอยู่!')
                return redirect('borrow_counter')

            due_date = timezone.now() + timedelta(days=duration_days)
            BorrowTransaction.objects.create(member=member, book=book, due_date=due_date, status='ACTIVE')
            
            book.status = 'BORROWED'
            book.save()

            messages.success(request, f'✅ ทำรายการสำเร็จ! {member.full_name} ยืม "{book.title}"')
            return redirect('borrow_counter')

        except (Member.DoesNotExist, Book.DoesNotExist, ValueError):
            messages.error(request, '⚠️ ข้อมูลไม่ถูกต้อง หรือไม่พบในระบบ')

    return render(request, 'library_app/borrow/create_tx.html')

# ==========================================
# Module 6: Return Processing
# ==========================================
def return_counter(request):
    if not request.session.get('is_admin'): return redirect('index')

    query_ssid = request.GET.get('ssid', '')
    member = None
    active_txs = []

    if query_ssid:
        try:
            member = Member.objects.get(ssid=query_ssid)
            active_txs = member.transactions.filter(status='ACTIVE').order_by('start_date')
        except Member.DoesNotExist:
            messages.error(request, '⚠️ ไม่พบรหัสสมาชิก (SSID) นี้ในระบบ')

    return render(request, 'library_app/borrow/record.html', {'member': member, 'active_txs': active_txs, 'query_ssid': query_ssid})

def process_return(request, tx_id):
    if not request.session.get('is_admin'): return redirect('index')

    tx = get_object_or_404(BorrowTransaction, tx_id=tx_id)
    
    if tx.status == 'ACTIVE':
        tx.returned_at = timezone.now()
        tx.status = 'RETURNED'
        tx.book.status = 'AVAILABLE'
        tx.book.save()
        
        if tx.returned_at > tx.due_date:
            overdue_days = (tx.returned_at - tx.due_date).days
            tx.fine_amount = overdue_days * 10.00 if overdue_days > 0 else 0
                
        tx.save()
        
        if tx.fine_amount > 0:
            messages.error(request, f'⚠️ รับคืนแล้ว (มีค่าปรับ {tx.fine_amount} บาท!)')
        else:
            messages.success(request, f'✅ รับคืนเรียบร้อยแล้ว')
            
    return redirect(f"/record/?ssid={tx.member.ssid}")

# ==========================================
# Module 7: Transaction History
# ==========================================
def transaction_history(request):
    if not request.session.get('is_admin'): return redirect('index')

    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    txs = BorrowTransaction.objects.all().order_by('-start_date')

    if query:
        txs = txs.filter(Q(member__ssid__icontains=query) | Q(book__book_id__icontains=query) | Q(book__title__icontains=query))
    if status_filter:
        txs = txs.filter(status=status_filter)

    return render(request, 'library_app/transaction/list.html', {'transactions': txs, 'query': query, 'status_filter': status_filter})

# ==========================================
# Module 8: Admin Settings
# ==========================================
def admin_settings(request):
    if not request.session.get('is_admin'): return redirect('index')
    
    admin = Member.objects.get(ssid=request.session['member_id'])
    return render(request, 'library_app/admin/settings.html', {'admin': admin})

def change_password(request):
    if not request.session.get('is_admin'): return redirect('index')

    if request.method == 'POST':
        current_pw, new_pw, confirm_pw = request.POST.get('current_password'), request.POST.get('new_password'), request.POST.get('confirm_password')
        admin = Member.objects.get(ssid=request.session['member_id'])
        
        if not admin.check_password(current_pw):
            messages.error(request, '❌ รหัสผ่านปัจจุบันไม่ถูกต้อง')
        elif new_pw != confirm_pw:
            messages.error(request, '❌ รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน')
        else:
            admin.set_password(new_pw)
            admin.save()
            messages.success(request, '✅ อัปเดตรหัสผ่านสำเร็จ!')

    return redirect('admin_settings')


# ==========================================
# Module 9: Admin Dashboard (Data Visualization with Pandas)
# ==========================================
def admin_dashboard(request):
    """ หน้า Dashboard ดึงข้อมูลจากฐานข้อมูลจริงมาทำกราฟด้วย Pandas/Plotly """
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

    # ----------------------------------------------------
    # ส่วนทำ Data Visualization จากฐานข้อมูลจริง (20 Records)
    # ----------------------------------------------------
    txs = BorrowTransaction.objects.select_related('book').all()
    
    chart_config = {'displayModeBar': False, 'responsive': True}
    
    if not txs.exists():
        # กรณีไม่มีข้อมูลในฐานข้อมูล
        empty_msg = "<div style='text-align:center; padding: 2rem; color: #9ca3af;'>ยังไม่มีประวัติการยืมในระบบ</div>"
        graph1_html = graph2_html = graph3_bar_html = graph3_pie_html = empty_msg
    else:
        # เตรียมแปลงข้อมูล QuerySet ให้เป็น Dictionary สำหรับ Pandas
        data = []
        thai_days = {
            'Monday': 'วันจันทร์', 'Tuesday': 'วันอังคาร', 'Wednesday': 'วันพุธ',
            'Thursday': 'วันพฤหัสบดี', 'Friday': 'วันศุกร์', 'Saturday': 'วันเสาร์', 'Sunday': 'วันอาทิตย์'
        }
        
        for tx in txs:
            day_name = tx.start_date.strftime('%A')
            visit_day = thai_days.get(day_name, day_name)
            
            # คำนวณระยะเวลายืม/คืนเป็นจำนวนวัน
            if tx.returned_at:
                borrow_duration = (tx.returned_at - tx.start_date).days
            else:
                borrow_duration = (tx.due_date - tx.start_date).days
            
            # ป้องกันกรณีคืนภายในวันเดียวกัน ให้ถือเป็น 1 วัน
            if borrow_duration <= 0:
                borrow_duration = 1
                
            data.append({
                'visit_day': visit_day,
                'book_category': tx.book.category,
                'borrow_duration': borrow_duration
            })
            
        df = pd.DataFrame(data)

        # กราฟที่ 1: จำนวนคนที่เข้าต่อวัน (วันจันทร์ - เสาร์)
        day_order = ['วันจันทร์', 'วันอังคาร', 'วันพุธ', 'วันพฤหัสบดี', 'วันศุกร์', 'วันเสาร์']
        df_days = df['visit_day'].value_counts().reindex(day_order).fillna(0).reset_index()
        df_days.columns = ['วัน', 'จำนวนคน']
        
        fig1 = px.bar(df_days, x='วัน', y='จำนวนคน', 
                      title='1. จำนวนผู้ใช้บริการต่อวัน',
                      color_discrete_sequence=['#4338ca'])
        fig1.update_layout(margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        graph1_html = fig1.to_html(full_html=False, include_plotlyjs=False, config=chart_config)

        # กราฟที่ 2: คนยืมหนังสือประเภทไหน จำนวนต่อประเภท
        df_cats = df['book_category'].value_counts().reset_index()
        df_cats.columns = ['หมวดหมู่', 'จำนวน (ครั้ง)']
        
        fig2 = px.bar(df_cats, x='หมวดหมู่', y='จำนวน (ครั้ง)', 
                      title='2. การยืมแยกตามหมวดหมู่',
                      color='หมวดหมู่',
                      color_discrete_sequence=px.colors.qualitative.Pastel)
        fig2.update_layout(margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
        graph2_html = fig2.to_html(full_html=False, include_plotlyjs=False, config=chart_config)

        # กราฟที่ 3.1: ระยะเวลาการยืมหนังสือ (กราฟแท่ง)
        df_duration = df['borrow_duration'].value_counts().sort_index().reset_index()
        df_duration.columns = ['ระยะเวลา (วัน)', 'จำนวนคน']
        df_duration['ระยะเวลา (วัน)'] = df_duration['ระยะเวลา (วัน)'].astype(int).astype(str) + ' วัน'
        
        fig3_bar = px.bar(df_duration, x='ระยะเวลา (วัน)', y='จำนวนคน', 
                          title='3.1 ระยะเวลาในการยืม/คืน (จำนวนคน)',
                          text='จำนวนคน',
                          color_discrete_sequence=['#0d9488'])
        fig3_bar.update_layout(margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        graph3_bar_html = fig3_bar.to_html(full_html=False, include_plotlyjs=False, config=chart_config)

        # กราฟที่ 3.2: สัดส่วนระยะเวลาการยืม (กราฟโดนัท)
        fig3_pie = px.pie(df_duration, names='ระยะเวลา (วัน)', values='จำนวนคน', 
                          title='3.2 สัดส่วนระยะเวลา (%)',
                          hole=0.4,
                          color_discrete_sequence=px.colors.sequential.Teal)
        fig3_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig3_pie.update_layout(margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
        graph3_pie_html = fig3_pie.to_html(full_html=False, include_plotlyjs=False, config=chart_config)

    context = {
        'total_members':        total_members,
        'total_books':          total_books,
        'active_borrows':       active_borrows,
        'overdue_count':        overdue_count,
        'overdue_transactions': overdue_transactions,
        
        'graph1_html': graph1_html,
        'graph2_html': graph2_html,
        'graph3_bar_html': graph3_bar_html,
        'graph3_pie_html': graph3_pie_html,
    }

    return render(request, 'library_app/admin/dashboard.html', context)