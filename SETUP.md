# Quick Setup Guide

## Step 1: Navigate to Project Directory
```bash
cd healthcare
```

## Step 2: Create Database Tables
```bash
python manage.py makemigrations
python manage.py migrate
```

## Step 3: Create Admin User
```bash
python manage.py createadmin
```

Default credentials:
- Username: `admin`
- Password: `admin123`
- Email: `admin@healthcare.com`

Or create with custom credentials:
```bash
python manage.py createadmin --username yourusername --email your@email.com --password yourpassword
```

## Step 4: Run Server
```bash
python manage.py runserver
```

## Step 5: Access Application
Open browser: http://127.0.0.1:8000/

## Testing the System

1. **Login as Admin:**
   - Use the credentials created in Step 3
   - You'll see the Admin Dashboard

2. **Register a Doctor:**
   - Logout
   - Go to Register page
   - Fill in details and select "Doctor" role
   - After registration, login will show "Pending Approval"

3. **Approve Doctor (as Admin):**
   - Login as Admin
   - Go to Admin Dashboard
   - Find the pending doctor in "Pending Doctor Approvals"
   - Click "Approve" button

4. **Register a Patient:**
   - Logout
   - Register with "Patient" role
   - Patient accounts are auto-approved

5. **Register a Hospital:**
   - Similar to Doctor, requires admin approval

## Key Features Implemented

✅ Custom User Model (AbstractUser)
✅ Role-based Authentication (Admin, Doctor, Patient, Hospital)
✅ Registration with role selection
✅ Login/Logout functionality
✅ Role-based dashboard redirection
✅ Admin approval system for Doctors and Hospitals
✅ Modern UI with Bootstrap 5
✅ Security mixins for role-based access control
✅ Custom admin dashboard (Django admin disabled)

## Next Steps

You can now extend the system by:
- Adding appointment booking functionality
- Implementing document upload
- Creating profile management pages
- Adding more features to each dashboard
