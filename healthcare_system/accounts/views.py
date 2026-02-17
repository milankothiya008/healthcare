from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .models import User
from patients.models import PatientProfile
from doctors.models import DoctorProfile
from hospitals.models import HospitalProfile
from documents.models import Document
from django.contrib.auth import authenticate, logout
from django.contrib.auth.decorators import login_required


def register_view(request):
    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")
        role = request.POST.get("role")

        # Create user
        user = User.objects.create_user(
            email=email,
            password=password,
            role=role
        )

        # Patient
        if role == "patient":
            PatientProfile.objects.create(
                user=user,
                first_name=request.POST.get("p_first_name"),
                last_name=request.POST.get("p_last_name"),
                gender=request.POST.get("p_gender"),
                date_of_birth=request.POST.get("p_dob"),
                phone=request.POST.get("p_phone"),
                address=request.POST.get("p_address"),
            )

            login(request, user)
            return redirect("patient_dashboard")

        # Doctor
        elif role == "doctor":
            doctor = DoctorProfile.objects.create(
                user=user,
                first_name=request.POST.get("d_first_name"),
                last_name=request.POST.get("d_last_name"),
                specialization=request.POST.get("specialization"),
                experience_years=request.POST.get("experience"),
                phone=request.POST.get("d_phone"),
                hospital_name=request.POST.get("hospital_name"),
                status="pending"
            )

            if request.FILES.get("document"):
                Document.objects.create(
                    user=user,
                    document_type="license",
                    file=request.FILES.get("document")
                )

            messages.success(request, "Registration successful. Wait for admin approval.")
            return redirect("login")

        # Hospital
        elif role == "hospital":
            hospital = HospitalProfile.objects.create(
                user=user,
                hospital_name=request.POST.get("hospital_name"),
                phone=request.POST.get("h_phone"),
                address=request.POST.get("h_address"),
                city=request.POST.get("city"),
                state=request.POST.get("state"),
                status="pending"
            )

            if request.FILES.get("document"):
                Document.objects.create(
                    user=user,
                    document_type="hospital_certificate",
                    file=request.FILES.get("document")
                )

            messages.success(request, "Registration successful. Wait for admin approval.")
            return redirect("login")

    return render(request, "register.html")
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from doctors.models import DoctorProfile
from hospitals.models import HospitalProfile


def login_view(request):

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:

            # 🔹 Doctor Approval Check
            if user.role == "doctor":
                doctor_profile = DoctorProfile.objects.filter(user=user).first()

                if not doctor_profile:
                    messages.error(request, "Doctor profile not found.")
                    return redirect("login")

                if doctor_profile.status != "approved":
                    messages.error(request, "Doctor account not approved yet.")
                    return redirect("login")

            # 🔹 Hospital Approval Check
            if user.role == "hospital":
                hospital_profile = HospitalProfile.objects.filter(user=user).first()

                if not hospital_profile:
                    messages.error(request, "Hospital profile not found.")
                    return redirect("login")

                if hospital_profile.status != "approved":
                    messages.error(request, "Hospital account not approved yet.")
                    return redirect("login")

            # 🔹 If everything OK → Login
            login(request, user)

            # 🔹 Redirect based on role
            if user.role == "admin":
                return redirect("admin_dashboard")

            elif user.role == "doctor":
                return redirect("doctor_dashboard")

            elif user.role == "patient":
                return redirect("patient_dashboard")

            elif user.role == "hospital":
                return redirect("hospital_dashboard")

        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "login.html")

@login_required
def patient_dashboard(request):
    return render(request, "dashboard.html", {"role": "Patient"})

@login_required
def doctor_dashboard(request):
    return render(request, "dashboard.html", {"role": "Doctor"})

@login_required
def hospital_dashboard(request):
    return render(request, "dashboard.html", {"role": "Hospital"})

@login_required
def admin_dashboard(request):
    return render(request, "dashboard.html", {"role": "System Admin"})
