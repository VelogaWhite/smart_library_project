from django.db import models
from django.contrib.auth.models import AbstractUser

# TODO: เพื่อนๆ มาเติม Field ตาม Database Schema (Users, Books, Categories, Borrowing_Records, Fines)
class User(AbstractUser):
    pass

class Category(models.Model):
    pass

class Book(models.Model):
    pass

class BorrowingRecord(models.Model):
    pass

class Fine(models.Model):
    pass