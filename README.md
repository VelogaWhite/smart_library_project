# 📚 Smart Library Project (SSID Fast-Checkout Edition)

A modern, web-based Library Management System built with Django. This version of the project (the ssid-auth branch) is specifically designed for rapid counter service, utilizing an SSID-based authentication system to speed up physical book borrowing and returning.

# ✨ Key Features of the SSID Architecture

🚀 Rapid Counter Operations

Direct Borrow/Return: Librarians process transactions instantly at the front desk by simply scanning or entering the Member's SSID and the Book ID.

No Manual Approvals Required: Bypasses the traditional "request and approve" workflow for immediate in-person physical checkouts.

Automated Fines: The system automatically calculates overdue fines (฿10/day) upon book return.

🔐 Specialized Authentication

Passwordless Member Login: Members access their personal portal instantly using just their numeric SSID (e.g., 10000001). No passwords to forget.

Secure Admin Access: Librarians and Administrators use a two-step secure login (Admin SSID + Password) to access the management dashboard.

📊 Management Dashboards

Admin Panel: Real-time statistics, inventory tracking, user management, and a comprehensive transaction history (Active, Returned, Overdue).

Member Portal: A clean UI for members to browse the library catalog, check availability, and monitor their active borrows and past reading history.

🛠️ Tech Stack

Backend: Python 3, Django 5.x

Frontend: HTML5, Tailwind CSS (via CDN)

Database: SQLite (Default) — Includes helper scripts (create_mssql_db.py, create_db.py) to easily swap to MS SQL Server or MariaDB via .env.

# 🚀 Installation & Setup

# 1. Clone the Repository and Switch Branch

Make sure you are on the ssid-auth branch to use this version of the system.

```git clone https://github.com/VelogaWhite/smart_library_project```

```cd smart_library_project```

```git checkout ssid-auth```


# 2. Setup a Virtual Environment

Create a virtual environment

```python -m venv venv```

Activate the virtual environment
  On Windows:
  ```venv\Scripts\activate```
  
  On macOS/Linux:
 ``` source venv/bin/activate```


# 3. Install Dependencies

```pip install -r requirements.txt```


# 4. Initialize the Database

Run Django's migration commands to build the database schema:

```python manage.py makemigrations library_app```

```python manage.py migrate```


# 5. Generate Mock Data (Highly Recommended)

Populate your local database with sample categories, books, users, and dummy transactions to easily test the system out of the box:


```python setup_data.py```


# 6. Run the Development Server

```python manage.py runserver```


Visit http://127.0.0.1:8000 in your web browser.

# 🔐 Default Login Credentials

If you ran the setup_data.py script in step 5, the following test accounts are available:

Librarian / Admin Account

SSID: 90000001

Password: admin123
(Enter this on the main landing page to be redirected to the Admin Auth screen).

Test Member Account

SSID: 10000001
(Enter this on the main landing page to view the member portal).

# 🧪 Running Automated Tests

This project includes a test suite covering form validation, model logic, and view access control. To run the tests:

python manage.py test library_app.tests
