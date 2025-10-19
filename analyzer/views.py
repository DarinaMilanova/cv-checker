from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .forms import AnalyzeUploadForm
from .utils import extract_text_any
from .models import Analysis
from .nlp_utils import analyze_texts
from django.contrib.auth import login, logout
from .forms import CustomRegisterForm, CustomLoginForm
from django.contrib.auth import get_user_model

_CATEGORY_LABELS = {
    "programming_languages": "Programming Languages",
    "frameworks_libraries": "Frameworks & Libraries",
    "web_technologies": "Web Technologies",
    "api_technologies": "APIs",
    "databases_relational": "Relational Databases",
    "databases_nonrelational": "NoSQL Databases",
    "databases_timeseries": "Time-Series Databases",
    "data_engineering": "Data Engineering",
    "data_science_ml": "Data Science & ML",
    "messaging_eventing": "Messaging & Eventing",
    "cloud_platforms": "Cloud Platforms",
    "containerization_orchestration": "Containers & Orchestration",
    "infrastructure_as_code": "Infrastructure as Code",
    "ci_cd_tooling": "CI/CD Tooling",
    "version_control": "Version Control",
    "observability_tooling": "Observability & Monitoring",
    "security": "Security",
    "qa_testing": "QA & Testing",
    "mobile_ios": "Mobile · iOS",
    "mobile_android": "Mobile · Android",
    "mobile_crossplatform": "Mobile · Cross-platform",
    "ui_ux": "UI/UX",
    "it_support": "IT Support",
    "sysadmin_linux": "SysAdmin · Linux",
    "sysadmin_windows": "SysAdmin · Windows",
    "networking": "Networking",
    "customer_support_tools": "Customer Support Tools",
    "project_methodologies": "Project Methodologies",
}

def pretty_category(cat_key: str) -> str:
    if not cat_key:
        return ""
    key = (cat_key or "").strip().lower()
    if key in _CATEGORY_LABELS:
        return _CATEGORY_LABELS[key]


    pretty = key.replace("_", " ").title()
    pretty = (
        pretty.replace("Api", "APIs")
             .replace("Ui Ux", "UI/UX")
             .replace("Ci Cd", "CI/CD")
             .replace("Ios", "iOS")
    )
    if pretty.startswith("Mobile Ios"):
        pretty = pretty.replace("Mobile Ios", "Mobile · iOS")
    if pretty.startswith("Mobile Android"):
        pretty = pretty.replace("Mobile Android", "Mobile · Android")
    if pretty.startswith("Mobile Crossplatform"):
        pretty = pretty.replace("Mobile Crossplatform", "Mobile · Cross-platform")
    if pretty.startswith("Sysadmin "):
        pretty = pretty.replace("Sysadmin ", "SysAdmin · ")
    return pretty


@login_required
def home(request):
    if request.method == "POST":
        form = AnalyzeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            cv_file = form.cleaned_data.get("cv")
            jd_file = form.cleaned_data.get("jd")
            cv_text = form.cleaned_data.get("cv_text")
            jd_text = form.cleaned_data.get("jd_text")

            job_title = form.cleaned_data.get("job_title") or ""
            company = form.cleaned_data.get("company") or ""


            if not cv_text and cv_file:
                cv_text = extract_text_any(cv_file)
            if not jd_text and jd_file:
                jd_text = extract_text_any(jd_file)

            if cv_file:
                cv_file.seek(0)
            if jd_file:
                jd_file.seek(0)


            results = analyze_texts(cv_text, jd_text)

            analysis = Analysis.objects.create(
                user=request.user,
                job_title=job_title,
                company=company,
                cv_file=cv_file,
                jd_file=jd_file,
                cv_text=cv_text,
                jd_text=jd_text,
                match_percent=results["match_percent"],
                cv_keywords=results["cv_keywords"],
                jd_keywords=results["jd_keywords"],
            )

            return redirect("analysis_detail", pk=analysis.pk)
        else:
            return render(request, "analyzer/analyse.html", {"form": form})

    return render(request, "analyzer/analyse.html", {"form": AnalyzeUploadForm()})

@login_required
def analysis_history(request):
    analyses = Analysis.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "analyzer/analysis-history.html", {"analyses": analyses})


@login_required
def analysis_detail(request, pk):
    analysis = get_object_or_404(Analysis, pk=pk, user=request.user)
    results = analyze_texts(analysis.cv_text, analysis.jd_text)


    table_rows = []
    cat_scores = results.get("category_scores", {})
    mbc = results.get("matched_by_category", {})
    mibc = results.get("missing_by_category", {})
    xbc = results.get("extra_by_category", {})


    all_keys = set(cat_scores) | set(mbc) | set(mibc) | set(xbc)
    for cat_key in sorted(all_keys):
        score = cat_scores.get(cat_key, 0.0)
        table_rows.append({
            "cat_key": cat_key,
            "cat_pretty": pretty_category(cat_key),
            "score": score,
            "matched": ", ".join(mbc.get(cat_key, [])),
            "missing": ", ".join(mibc.get(cat_key, [])),
            "extra": ", ".join(xbc.get(cat_key, [])),
        })

    context = {
        "analysis": analysis,
        "match_percent": results.get("match_percent"),
        "ai_result_text": results.get("ai_result_text"),
        "jd_level": results.get("jd_level", {}),
        "cv_level": results.get("cv_level", {}),
        "recommendations": results.get("recommendations", []),
        "matched_keywords": results.get("matched_keywords", []),
        "missing_keywords": results.get("missing_keywords", []),
        "extra_keywords": results.get("extra_keywords", []),
        "table_rows": table_rows,

        "evidence": results.get("evidence", {}),
    }
    return render(request, "analyzer/result-details.html", context)


@login_required
def delete_analysis(request, pk):
    analysis = get_object_or_404(Analysis, pk=pk, user=request.user)
    if request.method == "POST":
        analysis.delete()
        if request.headers.get("HX-Request") == "true":
            return HttpResponse("")
        messages.success(request, "Analysis deleted successfully.")
    return redirect("analysis_history")

def about(request):
    return render(request, "analyzer/about.html")

def register_view(request):
    if request.method == "POST":
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created and logged in.")
            return redirect("home")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomRegisterForm()
    return render(request, "analyzer/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, "Logged in successfully.")
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = CustomLoginForm()
    return render(request, "analyzer/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "Logged out.")
    return redirect("login")


@login_required
def account_info(request):
    return render(request, "analyzer/account.html", {"u": request.user})

User = get_user_model()
@login_required
def delete_account(request):
    if request.method == "POST":
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Your account has been deleted.")
        return redirect("login")
    return redirect("account_info")