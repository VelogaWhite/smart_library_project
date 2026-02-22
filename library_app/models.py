from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = [('Librarian', 'Librarian'), ('Member', 'Member')]
    Role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Member')
    FullName = models.CharField(max_length=255, blank=True, default='')

class Category(models.Model):
    CategoryName = models.CharField(max_length=100)
    def __str__(self): return self.CategoryName

class Book(models.Model):
    Title = models.CharField(max_length=255)
    CategoryID = models.ForeignKey(Category, on_delete=models.CASCADE)
    AuthorName = models.CharField(max_length=255, default='Unknown')
    ISBN = models.CharField(max_length=20, unique=True)
    TotalCopies = models.IntegerField(default=1)
    AvailableCopies = models.IntegerField(default=1)
    def __str__(self): return self.Title

class BorrowingRecord(models.Model):
    UserID = models.ForeignKey(User, on_delete=models.CASCADE)
    BookID = models.ForeignKey(Book, on_delete=models.CASCADE)
    BorrowDate = models.DateTimeField(auto_now_add=True)
    DueDate = models.DateTimeField(null=True, blank=True)
    ReturnDate = models.DateTimeField(null=True, blank=True)
    Status = models.CharField(max_length=20, default='Active')

class Fine(models.Model):
    BorrowID = models.ForeignKey(BorrowingRecord, on_delete=models.CASCADE)
    FineAmount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    Status = models.CharField(max_length=10, default='Unpaid')