# Healthcare Management System

A comprehensive Django-based healthcare management system with role-based access control.

## Features

- **Custom User Model** with roles: Admin, Doctor, Patient, Hospital
- **Role-based Authentication** with secure login/logout
- **Admin Dashboard** for system management
- **Doctor Dashboard** for managing appointments
- **Patient Dashboard** for viewing appointments and documents
- **Hospital Dashboard** for hospital management
- **Approval System** for Doctors and Hospitals (requires admin approval)
- **Modern UI** with Bootstrap 5 and responsive design

## Installation

1. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # Linux/Mac
   ```

2. **Install dependencies:**
   ```bash
   pip install django
   ```

3. **Run migrations:**
   ```bash
   cd healthcare
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Create admin user:**
   ```bash
   python manage.py createadmin
   # Or with custom credentials:
   python manage.py createadmin --username admin --email admin@example.com --password yourpassword
   ```

5. **Run development server:**
   ```bash
   python manage.py runserver
   ```

6. **Access the application:**
   - Open browser: http://127.0.0.1:8000/
   - Login with admin credentials

## Project Structure

```
healthcare/
├── accounts/          # User authentication and dashboards
├── patients/          # Patient profiles and management
├── doctors/           # Doctor profiles and management
├── hospitals/         # Hospital profiles and management
├── appointments/      # Appointment booking system
├── documents/         # Medical document management
├── templates/         # HTML templates
└── healthcare/        # Project settings
```

## User Roles

### Admin
- Full system access
- Approve/reject Doctor and Hospital registrations
- View all statistics and manage users

### Doctor
- Requires admin approval after registration
- Manage appointments
- View patient information
- Upload medical documents

### Patient
- Auto-approved after registration
- Book appointments
- View medical documents
- Manage profile

### Hospital
- Requires admin approval after registration
- Manage hospital information
- View appointments
- Manage doctors

## URLs

- `/` - Home (redirects to login or dashboard)
- `/accounts/register/` - User registration
- `/accounts/login/` - User login
- `/accounts/logout/` - User logout
- `/accounts/dashboard/` - Role-based dashboard redirect
- `/accounts/admin/dashboard/` - Admin dashboard
- `/accounts/doctor/dashboard/` - Doctor dashboard
- `/accounts/patient/dashboard/` - Patient dashboard
- `/accounts/hospital/dashboard/` - Hospital dashboard

## Security Features

- Role-based access control (RBAC)
- LoginRequiredMixin for protected views
- Role-specific mixins (AdminRequiredMixin, DoctorRequiredMixin, etc.)
- Approval system for sensitive roles
- CSRF protection
- Password validation

## Development

### Creating a new admin user:
```bash
python manage.py createadmin --username admin --email admin@example.com --password admin123
```

### Running tests:
```bash
python manage.py test
```

## Notes

- Django admin is disabled (as per requirements)
- Custom admin dashboard is implemented
- Media files are stored in `media/` directory
- Static files are collected in `staticfiles/` directory

## License

This project is for educational purposes.
