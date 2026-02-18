from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import User
from patients.models import PatientProfile
from doctors.models import DoctorProfile
from hospitals.models import HospitalProfile
from documents.models import Document



def register_view(request):
    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")
        role = request.POST.get("role")


        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("register")


        user = User.objects.create_user(
            email=email,
            password=password,
            role=role
        )


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


        elif role == "doctor":
            DoctorProfile.objects.create(
                user=user,
                first_name=request.POST.get("d_first_name"),
                last_name=request.POST.get("d_last_name"),
                specialization=request.POST.get("specialization"),
                experience_years=request.POST.get("experience"),
                phone=request.POST.get("d_phone"),
                hospital_name=request.POST.get("hospital_name"),
                profile_photo=request.FILES.get("profile_photo"),
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

        elif role == "hospital":
            HospitalProfile.objects.create(
                user=user,
                hospital_name=request.POST.get("hospital_name"),
                phone=request.POST.get("h_phone"),
                address=request.POST.get("h_address"),
                city=request.POST.get("city"),
                state=request.POST.get("state"),
                profile_photo=request.FILES.get("profile_photo"),
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



def login_view(request):

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is None:
            messages.error(request, "Invalid email or password.")
            return redirect("login")

        if user.is_blocked:
            messages.error(request, "Your account has been blocked by admin.")
            return redirect("login")

        if user.role == "doctor":
            doctor_profile = DoctorProfile.objects.filter(user=user).first()

            if not doctor_profile:
                messages.error(request, "Doctor profile not found.")
                return redirect("login")

            if doctor_profile.status != "approved":
                messages.error(request, "Doctor account not approved yet.")
                return redirect("login")

        if user.role == "hospital":
            hospital_profile = HospitalProfile.objects.filter(user=user).first()

            if not hospital_profile:
                messages.error(request, "Hospital profile not found.")
                return redirect("login")

            if hospital_profile.status != "approved":
                messages.error(request, "Hospital account not approved yet.")
                return redirect("login")

        login(request, user)

        if user.role == "admin":
            return redirect("admin_dashboard")
        elif user.role == "doctor":
            return redirect("doctor_dashboard")
        elif user.role == "patient":
            return redirect("patient_dashboard")
        elif user.role == "hospital":
            return redirect("hospital_dashboard")

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

    if request.user.role != "admin":
        return redirect("login")

    total_doctors = DoctorProfile.objects.count()
    total_patients = PatientProfile.objects.count()
    total_hospitals = HospitalProfile.objects.count()

    pending_doctors = DoctorProfile.objects.filter(status="pending")
    pending_hospitals = HospitalProfile.objects.filter(status="pending")

    context = {
        "total_doctors": total_doctors,
        "total_patients": total_patients,
        "total_hospitals": total_hospitals,
        "pending_doctors": pending_doctors,
        "pending_hospitals": pending_hospitals,
    }

    return render(request, "admin_dashboard.html", context)




@login_required
def approve_doctor(request, doctor_id):
    if request.user.role == "admin":
        doctor = DoctorProfile.objects.filter(id=doctor_id).first()
        if doctor:
            doctor.status = "approved"
            doctor.save()
    return redirect("admin_dashboard")


@login_required
def reject_doctor(request, doctor_id):
    if request.user.role == "admin":
        doctor = DoctorProfile.objects.filter(id=doctor_id).first()
        if doctor:
            doctor.status = "rejected"
            doctor.save()
    return redirect("admin_dashboard")


@login_required
def approve_hospital(request, hospital_id):
    if request.user.role == "admin":
        hospital = HospitalProfile.objects.filter(id=hospital_id).first()
        if hospital:
            hospital.status = "approved"
            hospital.save()
    return redirect("admin_dashboard")


@login_required
def reject_hospital(request, hospital_id):
    if request.user.role == "admin":
        hospital = HospitalProfile.objects.filter(id=hospital_id).first()
        if hospital:
            hospital.status = "rejected"
            hospital.save()
    return redirect("admin_dashboard")




@login_required
def doctor_detail(request, doctor_id):
    if request.user.role != "admin":
        return redirect("login")

    doctor = DoctorProfile.objects.filter(id=doctor_id).first()
    documents = Document.objects.filter(user=doctor.user) if doctor else []

    return render(request, "doctor_detail.html", {
        "doctor": doctor,
        "documents": documents,
    })


@login_required
def hospital_detail(request, hospital_id):
    if request.user.role != "admin":
        return redirect("login")

    hospital = HospitalProfile.objects.filter(id=hospital_id).first()
    documents = Document.objects.filter(user=hospital.user) if hospital else []

    return render(request, "hospital_detail.html", {
        "hospital": hospital,
        "documents": documents,
    })
