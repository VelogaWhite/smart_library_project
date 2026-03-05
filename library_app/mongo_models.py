from mongoengine import Document, StringField, IntField, BooleanField, DateTimeField, ReferenceField, DictField
from datetime import datetime

class MemberMongo(Document):
    ssid = IntField(required=True, unique=True)
    full_name = StringField(max_length=255, required=True)
    email = StringField(unique=True)
    phone_number = StringField(max_length=20)
    is_admin = BooleanField(default=False)
    
    created_at = DateTimeField(default=datetime.now)

    meta = {'collection': 'members', 'strict': False}

    def __str__(self):
        return f"[{self.ssid}] {self.full_name}"

class BookMongo(Document):
    book_id = IntField(required=True, unique=True)
    title = StringField(max_length=255, required=True)
    author = StringField(max_length=255)
    isbn = StringField(max_length=20)
    status = StringField(default='Available')
    
    # ฟิลด์อิสระ (Schema-less) สามารถยัดข้อมูลอะไรลงไปก็ได้โดยไม่ต้องแก้ Model
    extra_details = DictField()

    meta = {'collection': 'books', 'strict': False}

    def __str__(self):
        return f"[{self.book_id}] {self.title}"

class BorrowTransactionMongo(Document):
    # MongoDB ไม่ใช้ ForeignKey แต่ใช้ ReferenceField ในการอ้างอิง Document อื่น
    member = ReferenceField(MemberMongo, required=True)
    book = ReferenceField(BookMongo, required=True)
    
    start_date = DateTimeField(default=datetime.now)
    due_date = DateTimeField(required=True)
    returned_at = DateTimeField(null=True)
    status = StringField(default='ACTIVE')

    meta = {'collection': 'transactions', 'strict': False}