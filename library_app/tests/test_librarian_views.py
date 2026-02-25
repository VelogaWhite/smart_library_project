"""
=============================================================================
  Functional Tests — Module 6 & 7: Librarian Borrow & Return Dashboards
=============================================================================

Based on:
  - use_case_story.pdf  : Personas Sarah (Librarian) & Alex (Member)
  - Database_Schema.pdf : Users, Books, Categories, Borrowing_Records, Fines
  - project_map.pdf     : views.py / urls.py / templates structure

Story Context:
  Sarah is the librarian who logs in and manages the library's daily
  borrow/return operations through dedicated dashboards.
  Alex is the member who borrows and returns books.
  Non-librarians must be blocked from accessing these dashboards.

Run with:
  python manage.py test library_app.tests.test_librarian_views -v 2
=============================================================================
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from library_app.models import User, Category, Book, BorrowingRecord, Fine


# =============================================================================
# SHARED SETUP — Base class used by both dashboard test groups
# =============================================================================

class LibrarianDashboardBaseTest(TestCase):
    """
    Shared setUp following the User Story personas:
      - Sarah   → Librarian (the one who operates the dashboards)
      - Alex    → Member    (the one who borrows books)
      - Intruder → Member  (used to test access-control blocking)
    """

    @classmethod
    def setUpTestData(cls):
        # --- Personas from use_case_story.pdf ---
        cls.sarah = User.objects.create_user(
            username='sarah_lib',
            password='password123',
            Role='Librarian',
            FullName='Sarah Connor'
        )
        cls.alex = User.objects.create_user(
            username='alex_mem',
            password='password123',
            Role='Member',
            FullName='Alex Murphy'
        )
        cls.intruder = User.objects.create_user(
            username='intruder_mem',
            password='password123',
            Role='Member',
            FullName='Random Person'
        )

        # --- Books & Categories from Database_Schema.pdf ---
        cls.category = Category.objects.create(CategoryName='Technology')

        cls.book_available = Book.objects.create(
            Title='Python for Beginners',
            CategoryID=cls.category,
            AuthorName='John Doe',
            ISBN='ISBN-001',
            TotalCopies=5,
            AvailableCopies=5
        )
        cls.book_no_stock = Book.objects.create(
            Title='Advanced Django',
            CategoryID=cls.category,
            AuthorName='Jane Smith',
            ISBN='ISBN-002',
            TotalCopies=1,
            AvailableCopies=0     # Already fully borrowed
        )

    def setUp(self):
        # Fresh client for each test — avoids session bleed-over
        self.sarah_client = Client()
        self.alex_client  = Client()

        self.sarah_client.login(username='sarah_lib',   password='password123')
        self.alex_client.login( username='alex_mem',    password='password123')

        self.borrow_url  = reverse('librarian_borrow_dashboard')
        self.return_url  = reverse('librarian_return_dashboard')


# =============================================================================
# MODULE 6 — LIBRARIAN BORROW DASHBOARD
# =============================================================================

class LibrarianBorrowDashboardAccessTest(LibrarianDashboardBaseTest):
    """
    Tests: Who can see the borrow dashboard?
    Story: Sarah (Librarian) can access it. Alex (Member) must be blocked.
    """

    def test_sarah_librarian_can_access_borrow_dashboard(self):
        """
        MODULE 6 — Access Control (Pass)
        Sarah logs in as Librarian → should see the borrow dashboard (HTTP 200).
        """
        response = self.sarah_client.get(self.borrow_url)
        self.assertEqual(response.status_code, 200)

    def test_borrow_dashboard_uses_correct_template(self):
        """
        MODULE 6 — Template Check
        The correct HTML template must be rendered.
        """
        response = self.sarah_client.get(self.borrow_url)
        self.assertTemplateUsed(response, 'library_app/librarian_borrow_dashboard.html')

    def test_alex_member_is_blocked_from_borrow_dashboard(self):
        """
        MODULE 6 — Access Control (Block)
        Story: Only Librarians should operate the dashboard.
        Alex (Member) must NOT get HTTP 200 — should be redirected away.
        """
        response = self.alex_client.get(self.borrow_url)
        self.assertNotEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('search_books'))

    def test_unauthenticated_user_is_blocked_from_borrow_dashboard(self):
        """
        MODULE 6 — Access Control (Anonymous)
        Any visitor who is not logged in at all must be redirected to login.
        """
        anon_client = Client()
        response = anon_client.get(self.borrow_url)
        self.assertNotEqual(response.status_code, 200)

    def test_borrow_dashboard_context_contains_members_list(self):
        """
        MODULE 6 — Context: Member List
        The dropdown must be populated with Member-role users only (not Librarians).
        """
        response = self.sarah_client.get(self.borrow_url)
        members_in_context = list(response.context['members'])
        usernames = [u.username for u in members_in_context]

        self.assertIn('alex_mem', usernames)           # Alex (Member) should appear
        self.assertNotIn('sarah_lib', usernames)       # Sarah (Librarian) should NOT appear

    def test_borrow_dashboard_context_contains_available_books_only(self):
        """
        MODULE 6 — Context: Available Books
        Only books with AvailableCopies > 0 should appear in the dropdown.
        """
        response = self.sarah_client.get(self.borrow_url)
        available_books = list(response.context['available_books'])
        titles = [b.Title for b in available_books]

        self.assertIn('Python for Beginners', titles)   # Has stock → should appear
        self.assertNotIn('Advanced Django', titles)     # No stock → must NOT appear

    def test_borrow_dashboard_shows_active_borrow_count(self):
        """
        MODULE 6 — Context: Active Borrow Count
        The total_active counter in context must match the actual DB count.
        """
        response = self.sarah_client.get(self.borrow_url)
        db_count = BorrowingRecord.objects.filter(Status='Active').count()
        self.assertEqual(response.context['total_active'], db_count)


class LibrarianBorrowDashboardActionTest(LibrarianDashboardBaseTest):
    """
    Tests: Does the borrow action actually work and save to the database?
    Story: Sarah selects Alex + a book + duration, clicks Confirm Borrow.
           System records the transaction and updates book availability.
    """

    def _post_borrow(self, member_id, book_id, due_days=7):
        """Helper to POST a borrow action as Sarah."""
        return self.sarah_client.post(self.borrow_url, {
            'member_id': member_id,
            'book_id':   book_id,
            'due_days':  due_days,
        })

    def test_successful_borrow_creates_borrowing_record_in_db(self):
        """
        MODULE 6 — Core Logic: DB Record Created
        Story: 'System จะ Record Transaction' after borrow.
        After Sarah issues a borrow, a BorrowingRecord must exist in the DB.
        """
        self._post_borrow(self.alex.id, self.book_available.id)

        record_exists = BorrowingRecord.objects.filter(
            UserID=self.alex,
            BookID=self.book_available,
            Status='Active'
        ).exists()
        self.assertTrue(record_exists)

    def test_successful_borrow_decreases_available_copies(self):
        """
        MODULE 6 — Core Logic: Stock Decremented
        Story: 'Update Book Status' — AvailableCopies must drop by 1.
        """
        before = self.book_available.AvailableCopies  # 5
        self._post_borrow(self.alex.id, self.book_available.id)

        self.book_available.refresh_from_db()
        self.assertEqual(self.book_available.AvailableCopies, before - 1)

    def test_borrow_sets_correct_due_date(self):
        """
        MODULE 6 — Core Logic: Due Date Accuracy
        When Sarah selects 14 days, DueDate must be ~14 days from now.
        """
        self._post_borrow(self.alex.id, self.book_available.id, due_days=14)

        record = BorrowingRecord.objects.get(UserID=self.alex, BookID=self.book_available)
        expected_due = timezone.now() + timedelta(days=14)

        # Allow ±60 second tolerance for test execution time
        delta = abs((record.DueDate - expected_due).total_seconds())
        self.assertLess(delta, 60)

    def test_borrow_sets_status_to_active(self):
        """
        MODULE 6 — Core Logic: Status Field
        The new BorrowingRecord must have Status = 'Active'.
        """
        self._post_borrow(self.alex.id, self.book_available.id)
        record = BorrowingRecord.objects.get(UserID=self.alex, BookID=self.book_available)
        self.assertEqual(record.Status, 'Active')

    def test_borrow_redirects_back_to_borrow_dashboard_after_success(self):
        """
        MODULE 6 — UX: Redirect After POST
        After issuing a borrow, Sarah should stay on the borrow dashboard.
        """
        response = self._post_borrow(self.alex.id, self.book_available.id)
        self.assertRedirects(response, self.borrow_url)

    def test_cannot_borrow_book_with_no_available_copies(self):
        """
        MODULE 6 — Edge Case: No Stock
        book_no_stock has AvailableCopies=0. No record should be created.
        """
        initial_count = BorrowingRecord.objects.count()
        self._post_borrow(self.alex.id, self.book_no_stock.id)

        self.assertEqual(BorrowingRecord.objects.count(), initial_count)  # No new record
        self.book_no_stock.refresh_from_db()
        self.assertEqual(self.book_no_stock.AvailableCopies, 0)  # Stock unchanged

    def test_cannot_borrow_same_book_twice_for_same_member(self):
        """
        MODULE 6 — Edge Case: Duplicate Borrow Prevention
        If Alex already has 'Python for Beginners', issuing it again must be blocked.
        """
        # Issue once
        self._post_borrow(self.alex.id, self.book_available.id)
        count_after_first = BorrowingRecord.objects.filter(
            UserID=self.alex, BookID=self.book_available, Status='Active'
        ).count()
        self.assertEqual(count_after_first, 1)

        # Try to issue again
        self._post_borrow(self.alex.id, self.book_available.id)
        count_after_second = BorrowingRecord.objects.filter(
            UserID=self.alex, BookID=self.book_available, Status='Active'
        ).count()

        # Must still be only 1 — duplicate blocked
        self.assertEqual(count_after_second, 1)

    def test_member_cannot_post_borrow_action(self):
        """
        MODULE 6 — Security: Member Cannot POST
        Even if Alex somehow submits the borrow form, it must be blocked.
        """
        initial_count = BorrowingRecord.objects.count()
        self.alex_client.post(self.borrow_url, {
            'member_id': self.alex.id,
            'book_id':   self.book_available.id,
            'due_days':  7,
        })
        # No new records should have been created by a Member
        self.assertEqual(BorrowingRecord.objects.count(), initial_count)


# =============================================================================
# MODULE 7 — LIBRARIAN RETURN DASHBOARD
# =============================================================================

class LibrarianReturnDashboardAccessTest(LibrarianDashboardBaseTest):
    """
    Tests: Who can see the return dashboard?
    """

    def test_sarah_librarian_can_access_return_dashboard(self):
        """
        MODULE 7 — Access Control (Pass)
        Sarah (Librarian) must see the return dashboard (HTTP 200).
        """
        response = self.sarah_client.get(self.return_url)
        self.assertEqual(response.status_code, 200)

    def test_return_dashboard_uses_correct_template(self):
        """
        MODULE 7 — Template Check
        """
        response = self.sarah_client.get(self.return_url)
        self.assertTemplateUsed(response, 'library_app/librarian_return_dashboard.html')

    def test_alex_member_is_blocked_from_return_dashboard(self):
        """
        MODULE 7 — Access Control (Block)
        Alex (Member) must be redirected away from the return dashboard.
        """
        response = self.alex_client.get(self.return_url)
        self.assertNotEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('search_books'))

    def test_unauthenticated_user_is_blocked_from_return_dashboard(self):
        """
        MODULE 7 — Access Control (Anonymous)
        """
        anon_client = Client()
        response = anon_client.get(self.return_url)
        self.assertNotEqual(response.status_code, 200)

    def test_return_dashboard_context_shows_active_records(self):
        """
        MODULE 7 — Context: Active Records List
        Active borrow records must appear in the return dashboard's table.
        """
        # Create an active borrow record first
        record = BorrowingRecord.objects.create(
            UserID=self.alex,
            BookID=self.book_available,
            DueDate=timezone.now() + timedelta(days=7),
            Status='Active'
        )

        response = self.sarah_client.get(self.return_url)
        active_ids = [r.id for r in response.context['active_records']]
        self.assertIn(record.id, active_ids)

    def test_return_dashboard_context_shows_correct_counts(self):
        """
        MODULE 7 — Context: Stats Counters
        active_count and overdue_count must match the real DB state.
        """
        # One on-time, one overdue
        BorrowingRecord.objects.create(
            UserID=self.alex, BookID=self.book_available,
            DueDate=timezone.now() + timedelta(days=7),
            Status='Active'
        )
        BorrowingRecord.objects.create(
            UserID=self.intruder, BookID=self.book_available,
            DueDate=timezone.now() - timedelta(days=3),  # Past due = overdue
            Status='Active'
        )

        response = self.sarah_client.get(self.return_url)
        self.assertGreaterEqual(response.context['active_count'], 2)
        self.assertGreaterEqual(response.context['overdue_count'], 1)


class LibrarianReturnDashboardActionTest(LibrarianDashboardBaseTest):
    """
    Tests: Does the return action work correctly and save to the database?
    Story: Alex brings the book back → Sarah processes the return.
           System restores availability and calculates fines if overdue.
    """

    def setUp(self):
        super().setUp()

        # Pre-create an active borrow record to return during each test
        self.book_available.AvailableCopies = 4  # Simulating 1 already borrowed
        self.book_available.save()

        self.active_record = BorrowingRecord.objects.create(
            UserID=self.alex,
            BookID=self.book_available,
            DueDate=timezone.now() + timedelta(days=7),
            Status='Active'
        )

    def _post_return(self, borrow_id):
        """Helper to POST a return action as Sarah."""
        return self.sarah_client.post(self.return_url, {
            'borrow_id': borrow_id,
        })

    def test_successful_return_updates_status_to_returned(self):
        """
        MODULE 7 — Core Logic: Status Update
        Story: 'Sarah Process Return ผ่าน System ซึ่งจะ Update Status'
        After return, BorrowingRecord.Status must be 'Returned'.
        """
        self._post_return(self.active_record.id)
        self.active_record.refresh_from_db()
        self.assertEqual(self.active_record.Status, 'Returned')

    def test_successful_return_records_return_date(self):
        """
        MODULE 7 — Core Logic: ReturnDate Filled
        Schema: ReturnDate is NULL until returned. Must be filled after return.
        """
        self._post_return(self.active_record.id)
        self.active_record.refresh_from_db()
        self.assertIsNotNone(self.active_record.ReturnDate)

    def test_successful_return_restores_available_copies(self):
        """
        MODULE 7 — Core Logic: Stock Restored
        Story: 'System จะ Restore Availability ของหนังสือ'
        AvailableCopies must increase by 1 after return.
        """
        before = self.book_available.AvailableCopies  # 4
        self._post_return(self.active_record.id)

        self.book_available.refresh_from_db()
        self.assertEqual(self.book_available.AvailableCopies, before + 1)

    def test_return_redirects_back_to_return_dashboard_after_success(self):
        """
        MODULE 7 — UX: Redirect After POST
        Sarah should stay on the return dashboard after processing a return.
        """
        response = self._post_return(self.active_record.id)
        self.assertRedirects(response, self.return_url)

    def test_on_time_return_does_not_create_fine(self):
        """
        MODULE 7 — Fine Logic: No Fine for On-Time Return
        If returned before DueDate, no Fine record should be created.
        """
        # DueDate is 7 days from now → returning now = on time
        initial_fine_count = Fine.objects.count()
        self._post_return(self.active_record.id)
        self.assertEqual(Fine.objects.count(), initial_fine_count)  # No new fine

    def test_overdue_return_creates_fine_record_in_db(self):
        """
        MODULE 7 — Fine Logic: Fine Created for Late Return
        Story: If overdue, a Fine must be recorded in the Fines table (Schema).
        Set DueDate to 3 days ago → returning now = 3 days overdue.
        """
        # Make the record overdue
        self.active_record.DueDate = timezone.now() - timedelta(days=3)
        self.active_record.save()

        initial_fine_count = Fine.objects.count()
        self._post_return(self.active_record.id)

        # A Fine record must have been created
        self.assertEqual(Fine.objects.count(), initial_fine_count + 1)

    def test_overdue_fine_amount_is_calculated_correctly(self):
        """
        MODULE 7 — Fine Logic: Correct Fine Amount
        Rate is ฿5 per day. 3 days overdue → Fine must be ฿15.00.
        """
        self.active_record.DueDate = timezone.now() - timedelta(days=3)
        self.active_record.save()

        self._post_return(self.active_record.id)
        self.active_record.refresh_from_db()

        fine = Fine.objects.get(BorrowID=self.active_record)
        self.assertEqual(float(fine.FineAmount), 15.00)

    def test_overdue_fine_status_is_unpaid_by_default(self):
        """
        MODULE 7 — Fine Logic: Default Fine Status
        Schema: Fines.PaymentStatus — a new fine must default to 'Unpaid'.
        """
        self.active_record.DueDate = timezone.now() - timedelta(days=2)
        self.active_record.save()

        self._post_return(self.active_record.id)
        self.active_record.refresh_from_db()

        fine = Fine.objects.get(BorrowID=self.active_record)
        self.assertEqual(fine.Status, 'Unpaid')

    def test_returning_already_returned_record_does_nothing(self):
        """
        MODULE 7 — Edge Case: Double Return Prevention
        If Sarah accidentally clicks Return on an already-returned record,
        the system must silently ignore it — no crashes, no duplicate records.
        """
        # Return it once
        self._post_return(self.active_record.id)
        self.active_record.refresh_from_db()
        stock_after_first_return = self.book_available.AvailableCopies

        # Try to return it again
        self._post_return(self.active_record.id)
        self.book_available.refresh_from_db()

        # Stock should NOT increase again
        self.assertEqual(self.book_available.AvailableCopies, stock_after_first_return + 1)

    def test_member_cannot_post_return_action(self):
        """
        MODULE 7 — Security: Member Cannot POST
        Alex must not be able to process a return from his own client.
        """
        self.alex_client.post(self.return_url, {'borrow_id': self.active_record.id})
        self.active_record.refresh_from_db()

        # Status must remain Active — Member's POST was ignored
        self.assertEqual(self.active_record.Status, 'Active')


# =============================================================================
# INTEGRATION — Full Workflow Test (Sarah & Alex Together)
# =============================================================================

class FullBorrowReturnWorkflowTest(LibrarianDashboardBaseTest):
    """
    Tests: Complete end-to-end workflow matching the use_case_story.pdf narrative.
    Story: Sarah issues a book to Alex → Alex uses it → Alex returns it → Sarah processes return.
    """

    def test_full_borrow_and_return_workflow(self):
        """
        INTEGRATION — Full Workflow
        Story from use_case_story.pdf Part A: 'A Typical Day Using the System'

        Step 1: Sarah opens Borrow Dashboard and issues 'Python for Beginners' to Alex.
        Step 2: System records the transaction and decrements stock (Shared Visibility).
        Step 3: Alex brings the book back. Sarah opens Return Dashboard and processes it.
        Step 4: System restores stock. Returned record appears in Return History.
        """
        # --- STEP 1: Sarah issues the book ---
        self.sarah_client.post(reverse('librarian_borrow_dashboard'), {
            'member_id': self.alex.id,
            'book_id':   self.book_available.id,
            'due_days':  7,
        })

        # --- STEP 2: Verify transaction was recorded ---
        record = BorrowingRecord.objects.get(
            UserID=self.alex,
            BookID=self.book_available,
            Status='Active'
        )
        self.assertIsNotNone(record)

        self.book_available.refresh_from_db()
        self.assertEqual(self.book_available.AvailableCopies, 4)  # Was 5, now 4

        # --- STEP 3: Sarah processes the return ---
        self.sarah_client.post(reverse('librarian_return_dashboard'), {
            'borrow_id': record.id,
        })

        # --- STEP 4: Verify everything is restored ---
        record.refresh_from_db()
        self.book_available.refresh_from_db()

        self.assertEqual(record.Status, 'Returned')
        self.assertIsNotNone(record.ReturnDate)
        self.assertEqual(self.book_available.AvailableCopies, 5)  # Fully restored

        # Verify the record now shows in Return Dashboard history
        response = self.sarah_client.get(reverse('librarian_return_dashboard'))
        returned_ids = [r.id for r in response.context['returned_records']]
        self.assertIn(record.id, returned_ids)
