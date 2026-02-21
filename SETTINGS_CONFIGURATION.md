# Settings.py Configuration Summary

## 1. INSTALLED_APPS Setup

### Modified Section (Lines 33-47):
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Custom apps
    'accounts',        # User authentication and dashboards
    'patients',        # Patient profiles and management
    'doctors',         # Doctor profiles and management
    'hospitals',       # Hospital profiles and management
    'appointments',    # Appointment booking system
    'documents',       # Medical document management
]
```

**What was added:**
- `accounts` - Custom user model and authentication
- `patients` - Patient profile management
- `doctors` - Doctor profile management
- `hospitals` - Hospital management
- `appointments` - Appointment system
- `documents` - Medical documents

---

## 2. AUTH_USER_MODEL Configuration

### Added Section (Lines 121-122):
```python
# Custom User Model
AUTH_USER_MODEL = 'accounts.User'
```

**Explanation:**
- Points Django to use the custom User model from the `accounts` app
- Must be set before the first migration
- Format: `'app_name.ModelName'`
- This replaces Django's default User model

---

## 3. Authentication URLs Configuration

### Added Section (Lines 124-127):
```python
# Login URLs
LOGIN_URL = 'accounts:login'                    # Where to redirect unauthenticated users
LOGIN_REDIRECT_URL = 'accounts:dashboard_redirect'  # Where to redirect after login
LOGOUT_REDIRECT_URL = 'accounts:login'        # Where to redirect after logout
```

**Purpose:**
- `LOGIN_URL`: Redirects users trying to access protected pages without login
- `LOGIN_REDIRECT_URL`: Default redirect after successful login (then redirects based on role)
- `LOGOUT_REDIRECT_URL`: Where users go after logging out

---

## 4. Templates Configuration

### Modified Section (Line 64):
```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # ← Added this line
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
```

**What changed:**
- Added `'DIRS': [BASE_DIR / 'templates']` to include project-level templates directory
- Allows templates in `healthcare/templates/` to be found

---

## 5. Static Files Configuration

### Added Section (Lines 132-134):
```python
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']      # Where to find static files during development
STATIC_ROOT = BASE_DIR / 'staticfiles'        # Where to collect static files for production
```

**Purpose:**
- `STATIC_URL`: URL prefix for static files
- `STATICFILES_DIRS`: Additional directories to search for static files
- `STATIC_ROOT`: Directory where `collectstatic` collects all static files

---

## 6. Media Files Configuration

### Added Section (Lines 137-138):
```python
MEDIA_URL = 'media/'                          # URL prefix for media files
MEDIA_ROOT = BASE_DIR / 'media'               # Directory where uploaded files are stored
```

**Purpose:**
- `MEDIA_URL`: URL prefix for accessing uploaded media files
- `MEDIA_ROOT`: Physical directory where uploaded files (images, documents) are stored
- Used for: profile pictures, medical documents, hospital logos, etc.

---

## Complete Modified Sections Summary

### All Changes Made:

1. **INSTALLED_APPS** - Added 6 custom apps
2. **TEMPLATES['DIRS']** - Added templates directory
3. **AUTH_USER_MODEL** - Set to 'accounts.User'
4. **LOGIN_URL** - Set to 'accounts:login'
5. **LOGIN_REDIRECT_URL** - Set to 'accounts:dashboard_redirect'
6. **LOGOUT_REDIRECT_URL** - Set to 'accounts:login'
7. **STATIC_URL** - Set to 'static/'
8. **STATICFILES_DIRS** - Added BASE_DIR / 'static'
9. **STATIC_ROOT** - Set to BASE_DIR / 'staticfiles'
10. **MEDIA_URL** - Set to 'media/'
11. **MEDIA_ROOT** - Set to BASE_DIR / 'media'

---

## Important Notes

⚠️ **AUTH_USER_MODEL must be set before first migration:**
- If you've already run migrations, you'll need to delete the database and migrations
- Or create a fresh project with AUTH_USER_MODEL set from the start

⚠️ **App Order Matters:**
- Custom apps should be listed after Django's built-in apps
- `accounts` should be listed first among custom apps (since other apps depend on it)

⚠️ **Media Files in Production:**
- In production, serve media files through your web server (Nginx, Apache)
- Don't use Django's development server for media files in production
