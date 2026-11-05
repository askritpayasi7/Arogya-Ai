import json
import logging
import urllib.parse
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from health_app.config import settings
from health_app.dashboard.auth import GoogleOAuthManager
from health_app.dashboard.google_health import (
    GoogleFitnessClient,
    UserHealthData,
    DailySteps,
    DailyRecord,
    HeartRateSummary,
    SleepSummary,
    DailySleepRecord,
    resolve_user_timezone,
    load_user_history_cache,
    save_user_history_cache,
    generate_demo_history,
    generate_demo_weekly_sleep,
)
from health_app.dashboard.user_profile import (
    UserLifestyleProfile,
    load_user_profile,
    save_user_profile,
    get_default_demo_profile,
)
from health_app.dashboard.baseline_engine import (
    StatisticalBaselineEngine,
    UserBaselineReport,
    MetricBaseline,
)
from health_app.vectordb.store import (
    VectorStore,
    COLLECTION_RESEARCH,
    COLLECTION_FSSAI,
    COLLECTION_VERIFIED_RELATIONSHIPS,
)
from health_app.dashboard.biometric_advisor import BiometricAdvisor, CategoryVitalSummary
from health_app.fetcher.registry import PaperRegistry
from health_app.fetcher.client import PaperSearchClient, CandidatePaper
from health_app.fetcher.downloader import PDFDownloader
from health_app.relationships.pipeline import RelationshipPipeline
from health_app.prescription import (
    PrescriptionAnalyzer,
    PrescriptionRecord,
    PrescribedMedicineItem,
)
from health_app.dashboard.ask_ai import ClinicalAskAiAdvisor

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(
    title="VITA Evidence-Grounded Health App & Google Fitness Dashboard",
    description="Web dashboard connecting personal Google Health data with verified scientific research.",
    version="1.0.0"
)

# Encrypted session middleware for persistent auth state
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="vita_health_session",
    max_age=86400 * 7,  # 7 days
)


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Render modern landing page with Google Sign-in and Admin login options."""
    user = request.session.get("user")
    is_admin = request.session.get("is_admin", False)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"user": user, "is_admin": is_admin}
    )


@app.get("/api/auth/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth2 flow."""
    oauth = GoogleOAuthManager()
    if not oauth.configured:
        # If client secret is missing or not configured, offer a friendly message
        return HTMLResponse(
            "<h2>Google OAuth Credentials Not Configured</h2>"
            "<p>Please ensure client_secret_*.json is in the project root directory.</p>"
            "<p><a href='/dashboard?demo=true'>Continue to Demo Health Dashboard &rarr;</a></p>",
            status_code=400
        )

    auth_url = oauth.get_authorization_url(state="health_app_session")
    return RedirectResponse(auth_url, status_code=303)


@app.get("/api/auth/google/callback")
async def google_callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    """Handle Google OAuth2 redirect callback on Port 8001.
    Decoupled from heavy 180-day fetching so the redirect completes in <400ms without freezing.
    """
    if error or not code:
        logger.warning(f"Google OAuth error or empty code: {error}")
        return RedirectResponse("/?error=google_auth_failed", status_code=303)

    oauth = GoogleOAuthManager()
    try:
        token_data = oauth.exchange_code_for_tokens(code)
        access_token = token_data.get("access_token")
        profile = oauth.get_user_profile(access_token)

        request.session["user"] = profile
        request.session["access_token"] = access_token

        # Check if user has completed lifestyle onboarding questionnaire
        user_email = profile.get("email", "")
        existing_profile = load_user_profile(user_email)
        if not existing_profile or not existing_profile.onboarding_completed:
            return RedirectResponse("/onboarding", status_code=303)

        # Instant redirect! No heavy blocking fetch during callback
        return RedirectResponse("/dashboard", status_code=303)
    except Exception as e:
        logger.error(f"Error during Google callback token exchange: {e}")
        return HTMLResponse(
            f"<h3>Authentication Error</h3><p>{e}</p><p><a href='/'>&larr; Return to Home</a></p>",
            status_code=500
        )


@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding_view(request: Request):
    """Render medical & lifestyle onboarding questionnaire for new accounts."""
    session_user = request.session.get("user")
    user_email = session_user.get("email", "patient@example.com") if session_user else "patient@example.com"
    current_profile = load_user_profile(user_email)

    return templates.TemplateResponse(
        request=request,
        name="onboarding.html",
        context={
            "user_email": user_email,
            "current_profile": current_profile,
            "is_admin": request.session.get("is_admin", False)
        }
    )


@app.post("/api/user/onboarding")
async def save_onboarding_form(request: Request):
    """Save user lifestyle and medical profile submitted during onboarding."""
    session_user = request.session.get("user", {})
    try:
        form_data = await request.form()
        email = str(form_data.get("email", "")).strip()
        age = int(form_data.get("age", 28))
        profession = str(form_data.get("profession", "Desk Job / Engineer")).strip()
        smoking_status = str(form_data.get("smoking_status", "non_smoker"))
        alcohol_consumption = str(form_data.get("alcohol_consumption", "none"))
        chronic_factors = form_data.getlist("chronic_risk_factors") if hasattr(form_data, "getlist") else []
        primary_health_goal = str(form_data.get("primary_health_goal", "Cardiovascular & Sleep Health"))
    except Exception:
        # Resilient form parser without requiring external python-multipart
        raw_body = (await request.body()).decode("utf-8")
        parsed = urllib.parse.parse_qs(raw_body)
        email = parsed.get("email", [""])[0].strip()
        age = int(parsed.get("age", [28])[0])
        profession = parsed.get("profession", ["Desk Job / Engineer"])[0].strip()
        smoking_status = parsed.get("smoking_status", ["non_smoker"])[0]
        alcohol_consumption = parsed.get("alcohol_consumption", ["none"])[0]
        chronic_factors = parsed.get("chronic_risk_factors", [])
        primary_health_goal = parsed.get("primary_health_goal", ["Cardiovascular & Sleep Health"])[0]

    if not email and session_user:
        email = session_user.get("email", "")

    if not email:
        email = "patient@example.com"

    profile = UserLifestyleProfile(
        email=email,
        age=age,
        profession=profession,
        smoking_status=smoking_status,
        alcohol_consumption=alcohol_consumption,
        chronic_risk_factors=[str(f) for f in chronic_factors],
        primary_health_goal=primary_health_goal,
        baseline_status="active_calibrated" if age else "calibration_mode",
        onboarding_completed=True
    )

    save_user_profile(email, profile)
    return RedirectResponse("/dashboard", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request, demo: bool = False):
    """Render User Health Dashboard with personal biometrics and grounded clinical insights."""
    session_user = request.session.get("user")
    access_token = request.session.get("access_token")
    session_health = request.session.get("health_data")

    tz_offset = request.cookies.get("vita_tz_offset")
    tz_offset_minutes = int(tz_offset) if tz_offset and tz_offset.lstrip("-").isdigit() else None
    user_tz = resolve_user_timezone(tz_offset_minutes)

    if session_user and access_token and not demo:
        user_email = session_user.get("email", "")
        cached_history = load_user_history_cache(user_email)

        # Fast initial sync (today + 7D) if not yet in session
        if not session_health:
            try:
                fit_client = GoogleFitnessClient(access_token)
                health_data = fit_client.fetch_quick_health_data(
                    session_user,
                    tz_offset_minutes=tz_offset_minutes
                )
                session_dict = health_data.model_dump()
                session_dict["history_records"] = []
                request.session["health_data"] = session_dict
            except Exception as e:
                logger.warning(f"Quick sync error: {e}")
                health_data = UserHealthData(
                    user_name=session_user.get("name", "User"),
                    user_email=user_email,
                    user_picture=session_user.get("picture", ""),
                    is_live_data=True
                )
        else:
            health_data = UserHealthData(**session_health)
            # If weekly_sleep is missing from prior cached session, populate dynamically
            if not getattr(health_data.sleep, 'weekly_sleep', None):
                try:
                    fit_client = GoogleFitnessClient(access_token)
                    now_local = datetime.now(user_tz)
                    today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
                    s_ms = int((today_start - timedelta(days=6)).timestamp() * 1000)
                    e_ms = int((today_start + timedelta(days=1)).timestamp() * 1000)
                    health_data.sleep = fit_client._fetch_sleep(s_ms, e_ms, user_tz)
                except Exception as e:
                    logger.warning(f"Could not refresh sleep sessions: {e}")
                    health_data.sleep = generate_demo_weekly_sleep(user_tz)

        # Attach complete disk-cached history if available
        if cached_history:
            health_data.history_records = cached_history
    else:
        # Load realistic demo biometrics with 180-day history in preview mode
        demo_history = generate_demo_history(user_tz, days=180)
        today_steps = demo_history[-1].steps if demo_history else 11240
        demo_sleep = generate_demo_weekly_sleep(user_tz)
        health_data = UserHealthData(
            user_name="Demo Patient",
            user_email="patient@example.com",
            user_picture="",
            today_steps=today_steps,
            step_goal=10000,
            weekly_steps=[
                DailySteps(date=f"{r.day_name} ({r.formatted_date})", steps=r.steps)
                for r in demo_history[-7:]
            ],
            history_records=demo_history,
            heart_rate=HeartRateSummary(resting_bpm=71, min_bpm=58, max_bpm=128, latest_bpm=74),
            sleep=demo_sleep,
            is_live_data=False
        )

    # 1. Resolve User Lifestyle Profile
    if not health_data.is_live_data or demo:
        user_profile = get_default_demo_profile()
    else:
        user_profile = load_user_profile(health_data.user_email)
        if not user_profile:
            user_profile = UserLifestyleProfile(
                email=health_data.user_email,
                onboarding_completed=False
            )

    # 2. 15-Day Rolling Statistical Calibration Engine (μ ± 1.5σ) with EWMA Drift
    baseline_report = StatisticalBaselineEngine.evaluate_user_telemetry(
        email=health_data.user_email,
        history_records=health_data.history_records,
        acute_heart_rate=health_data.heart_rate.latest_bpm or health_data.heart_rate.resting_bpm,
        acute_sleep_hours=health_data.sleep.total_hours,
        acute_steps=health_data.today_steps
    )

    # 3. Multi-Modal Personalization Architecture: Metadata-Filtered Retrieval & Dynamic Context
    try:
        vector_store = VectorStore()
    except Exception as e:
        logger.debug(f"Vector store initialization deferred: {e}")
        vector_store = None

    insights = BiometricAdvisor.generate_personalized_insights(
        health_data=health_data,
        user_profile=user_profile,
        baseline_report=baseline_report,
        vector_store=vector_store
    )
    category_summaries = BiometricAdvisor.generate_category_summaries(
        health_data=health_data,
        user_profile=user_profile,
        baseline_report=baseline_report
    )
    history_json = json.dumps([r.model_dump() for r in health_data.history_records])
    weekly_sleep_json = json.dumps([r.model_dump() for r in getattr(health_data.sleep, 'weekly_sleep', [])])

    user = session_user or {"name": health_data.user_name, "email": health_data.user_email}
    needs_history_sync = bool(session_user and access_token and len(health_data.history_records) < 30)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "health_data": health_data,
            "user_profile": user_profile,
            "baseline_report": baseline_report,
            "history_json": history_json,
            "weekly_sleep_json": weekly_sleep_json,
            "insights": insights,
            "category_summaries": category_summaries,
            "needs_history_sync": needs_history_sync,
            "is_admin": request.session.get("is_admin", False)
        }
    )


# =========================================================================
# PRESCRIPTION ANALYZER & CLINICAL HISTORY ROUTES
# =========================================================================

@app.get("/dashboard/prescriptions", response_class=HTMLResponse)
async def prescriptions_page(request: Request, demo: bool = False):
    """Render dedicated prescription scanner & clinical verification interface."""
    session_user = request.session.get("user")
    email = session_user.get("email") if session_user else "patient@example.com"
    user_profile = load_user_profile(email)
    if not user_profile:
        user_profile = get_default_demo_profile() if (demo or not session_user) else UserLifestyleProfile(email=email)

    return templates.TemplateResponse(
        request=request,
        name="prescriptions.html",
        context={
            "user": session_user or ({"name": "Demo Patient", "email": email} if demo or not session_user else None),
            "user_profile": user_profile,
            "prescriptions": [p.to_compact_dict() for p in user_profile.prescriptions],
            "active_medications": [m.to_compact_dict() for m in user_profile.active_medications if m.included],
            "diagnosed_conditions": user_profile.diagnosed_conditions,
            "is_admin": request.session.get("is_admin", False),
        }
    )


@app.post("/api/prescriptions/analyze")
async def analyze_prescription_endpoint(request: Request):
    """Analyze uploaded prescription image, returning non-empty extracted fields for user review."""
    try:
        image_bytes: Optional[bytes] = None
        try:
            form = await request.form()
            file = form.get("prescription_image")
            if file and hasattr(file, "read"):
                image_bytes = await file.read()
            elif isinstance(file, bytes):
                image_bytes = file
        except Exception as form_err:
            logger.debug(f"request.form() failed, attempting fallback multipart parser: {form_err}")
            body = await request.body()
            content_type = request.headers.get("content-type", "")
            if "boundary=" in content_type:
                import email
                msg = email.message_from_bytes(f"Content-Type: {content_type}\r\n\r\n".encode("latin-1") + body)
                for part in msg.walk():
                    if part.get_filename() or part.get_content_type().startswith("image/"):
                        image_bytes = part.get_payload(decode=True)
                        break
            if not image_bytes and body:
                image_bytes = body

        if not image_bytes:
            return JSONResponse({"status": "error", "message": "No file uploaded or file is empty."}, status_code=400)

        analyzer = PrescriptionAnalyzer()
        extraction = analyzer.analyze_image(image_bytes)

        # Omit all empty / placeholder fields
        compact_data = extraction.to_compact_dict()
        return JSONResponse({"status": "success", "data": compact_data})
    except Exception as e:
        logger.error(f"Prescription vision extraction failed: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": f"Failed to analyze prescription: {str(e)}"}, status_code=500)


@app.post("/api/prescriptions/save")
async def save_prescription_endpoint(request: Request):
    """Save user-verified prescription, updating patient medical history and active medications."""
    session_user = request.session.get("user")
    email = session_user.get("email") if session_user else "patient@example.com"
    profile = load_user_profile(email)
    if not profile:
        profile = get_default_demo_profile() if not session_user else UserLifestyleProfile(email=email)

    try:
        payload = await request.json()
        meds_raw = payload.get("medicines", [])
        med_items: List[PrescribedMedicineItem] = []
        for m in meds_raw:
            if not isinstance(m, dict):
                continue
            if m.get("included", True) and m.get("name"):
                med_items.append(
                    PrescribedMedicineItem(
                        name=str(m["name"]).strip(),
                        strength=str(m["strength"]).strip() if m.get("strength") else None,
                        dosage=str(m["dosage"]).strip() if m.get("dosage") else None,
                        frequency=str(m["frequency"]).strip() if m.get("frequency") else None,
                        duration=str(m["duration"]).strip() if m.get("duration") else None,
                        route=str(m["route"]).strip() if m.get("route") else None,
                        instructions=str(m["instructions"]).strip() if m.get("instructions") else None,
                        notes=str(m["notes"]).strip() if m.get("notes") else None,
                        included=True,
                    )
                )

        diseases_raw = payload.get("diagnosed_diseases", [])
        clean_diseases = [str(d).strip() for d in diseases_raw if isinstance(d, str) and d.strip()]

        rx_record = PrescriptionRecord(
            id=payload.get("id") or uuid.uuid4().hex[:12],
            prescriber_name=str(payload["prescriber_name"]).strip() if payload.get("prescriber_name") else None,
            clinic_or_place=str(payload["clinic_or_place"]).strip() if payload.get("clinic_or_place") else None,
            prescription_date=str(payload["prescription_date"]).strip() if payload.get("prescription_date") else None,
            diagnosed_diseases=clean_diseases,
            medicines=med_items,
            raw_transcription=str(payload["raw_transcription"]).strip() if payload.get("raw_transcription") else None,
        )

        profile.add_prescription(rx_record)
        save_user_profile(email, profile)

        return JSONResponse({
            "status": "success",
            "message": "Prescription and patient clinical history successfully updated.",
            "prescription": rx_record.to_compact_dict(),
            "diagnosed_conditions": profile.diagnosed_conditions,
            "active_medications": [m.to_compact_dict() for m in profile.active_medications],
        })
    except Exception as e:
        logger.error(f"Error saving prescription: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.delete("/api/prescriptions/{rx_id}")
async def delete_prescription_endpoint(rx_id: str, request: Request):
    """Delete a prescription record by ID and re-evaluate active medications."""
    session_user = request.session.get("user")
    email = session_user.get("email") if session_user else "patient@example.com"
    profile = load_user_profile(email)
    if not profile:
        return JSONResponse({"status": "error", "message": "Profile not found."}, status_code=404)

    deleted = profile.delete_prescription(rx_id)
    if deleted:
        save_user_profile(email, profile)
        return JSONResponse({
            "status": "success",
            "message": "Prescription removed from clinical history.",
            "diagnosed_conditions": profile.diagnosed_conditions,
            "active_medications": [m.to_compact_dict() for m in profile.active_medications],
        })
    return JSONResponse({"status": "error", "message": "Prescription not found."}, status_code=404)


@app.get("/api/prescriptions/list")
async def list_prescriptions_endpoint(request: Request):
    """Fetch current user's prescriptions and active medications."""
    session_user = request.session.get("user")
    email = session_user.get("email") if session_user else "patient@example.com"
    profile = load_user_profile(email)
    if not profile:
        profile = get_default_demo_profile() if not session_user else UserLifestyleProfile(email=email)

    return JSONResponse({
        "status": "success",
        "prescriptions": [p.to_compact_dict() for p in profile.prescriptions],
        "active_medications": [m.to_compact_dict() for m in profile.active_medications],
        "diagnosed_conditions": profile.diagnosed_conditions,
    })


# =========================================================================
# ASK CLINICAL AI & RESEARCH INTELLIGENCE ROUTE
# =========================================================================

@app.post("/api/ai/ask")
async def ask_clinical_ai_endpoint(request: Request):
    """Personalized clinical Q&A answering user symptoms and questions with citations to peer-reviewed research."""
    session_user = request.session.get("user")
    email = session_user.get("email") if session_user else "patient@example.com"
    session_health = request.session.get("health_data")

    # 1. Load persistent user profile (with conditions, active medications, prescriptions)
    user_profile = load_user_profile(email)
    if not user_profile:
        user_profile = get_default_demo_profile() if not session_user else UserLifestyleProfile(email=email)

    # 2. Resolve health data & baseline anomalies
    tz_offset = request.cookies.get("vita_tz_offset")
    tz_offset_minutes = int(tz_offset) if tz_offset and tz_offset.lstrip("-").isdigit() else None
    user_tz = resolve_user_timezone(tz_offset_minutes)

    if session_health:
        health_data = UserHealthData(**session_health)
    else:
        cached_history = load_user_history_cache(email)
        demo_history = cached_history if cached_history else generate_demo_history(user_tz, days=30)
        today_steps = demo_history[-1].steps if demo_history else 8500
        health_data = UserHealthData(
            user_name="Patient",
            user_email=email,
            today_steps=today_steps,
            step_goal=10000,
            history_records=demo_history,
            heart_rate=HeartRateSummary(resting_bpm=72, min_bpm=60, max_bpm=120, latest_bpm=74),
            sleep=SleepSummary(total_hours=7.2, deep_sleep_hours=1.8, rem_sleep_hours=1.7, light_sleep_hours=3.2, awake_hours=0.5),
        )

    baseline_report = StatisticalBaselineEngine.evaluate_user_telemetry(
        email=email,
        history_records=health_data.history_records,
        acute_heart_rate=health_data.heart_rate.latest_bpm or health_data.heart_rate.resting_bpm,
        acute_sleep_hours=health_data.sleep.total_hours,
        acute_steps=health_data.today_steps,
    )

    try:
        vector_store = VectorStore()
    except Exception as e:
        logger.debug(f"Vector store deferred in ask_ai: {e}")
        vector_store = None

    try:
        body = await request.json()
        query = str(body.get("query", "")).strip()
        if not query:
            return JSONResponse({"status": "error", "message": "Query cannot be empty."}, status_code=400)

        result = ClinicalAskAiAdvisor.consult(
            query=query,
            health_data=health_data,
            user_profile=user_profile,
            baseline_report=baseline_report,
            vector_store=vector_store,
        )
        return JSONResponse({
            "status": "success",
            "result": result,
            "answer": result.get("direct_assessment", ""),
            "citations": result.get("cited_papers", []),
        })
    except Exception as e:
        logger.error(f"Error in Ask AI consultation: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": f"Clinical AI consultation failed: {str(e)}"}, status_code=500)



@app.post("/api/health/sync")
async def sync_health_data(request: Request):
    """Re-sync latest health metrics from Google Fit (quick sync)."""
    access_token = request.session.get("access_token")
    user_profile = request.session.get("user", {})

    if access_token:
        try:
            tz_offset = request.cookies.get("vita_tz_offset")
            tz_offset_minutes = int(tz_offset) if tz_offset and tz_offset.lstrip("-").isdigit() else None
            fit_client = GoogleFitnessClient(access_token)
            health_data = fit_client.fetch_quick_health_data(
                user_profile,
                tz_offset_minutes=tz_offset_minutes
            )
            session_health = health_data.model_dump()
            session_health["history_records"] = []  # Keep cookie small
            request.session["health_data"] = session_health
        except Exception as e:
            logger.warning(f"Sync error: {e}")

    return RedirectResponse("/dashboard", status_code=303)


@app.post("/api/health/sync-history")
async def sync_health_history(request: Request):
    """Background endpoint to backfill 180-day historical batches asynchronously."""
    access_token = request.session.get("access_token")
    user_profile = request.session.get("user", {})

    if not access_token:
        return {"status": "unauthenticated", "total_records": 0, "records": []}

    tz_offset = request.cookies.get("vita_tz_offset")
    tz_offset_minutes = int(tz_offset) if tz_offset and tz_offset.lstrip("-").isdigit() else None
    user_tz = resolve_user_timezone(tz_offset_minutes)
    email = user_profile.get("email", "")

    try:
        fit_client = GoogleFitnessClient(access_token)
        # Fetch batches in 30-day chunks up to 180 days
        history = fit_client.fetch_historical_batches(user_tz, max_days=180, batch_size=30)
        if history and email:
            save_user_history_cache(email, history)
            all_cached = load_user_history_cache(email)
            return {
                "status": "success",
                "total_records": len(all_cached),
                "records": [r.model_dump() for r in all_cached]
            }
        return {"status": "empty", "total_records": 0, "records": []}
    except Exception as e:
        logger.warning(f"Historical backfill error: {e}")
        return {"status": "error", "message": str(e), "total_records": 0, "records": []}


@app.post("/api/sync/trigger")
async def sync_trigger_endpoint(request: Request):
    """Background endpoint alias for client poller synchronization."""
    return await sync_health_history(request)


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, error: Optional[str] = None):
    """Render Admin login form."""
    if request.session.get("is_admin"):
        return RedirectResponse("/admin/dashboard", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="admin_login.html",
        context={"error": error, "user": None}
    )


@app.post("/admin/login")
async def admin_login_post(request: Request):
    """Handle Admin authentication."""
    password = ""
    # Parse form data with fallback to urlencoded body if python-multipart is absent
    try:
        body_bytes = await request.body()
        if body_bytes:
            parsed = urllib.parse.parse_qs(body_bytes.decode("utf-8", errors="replace"))
            if "password" in parsed:
                password = parsed["password"][0]
        if not password:
            form = await request.form()
            password = form.get("password", "")
    except Exception as e:
        logger.warning(f"Form parsing error: {e}")

    if password == settings.admin_password:
        request.session["is_admin"] = True
        return RedirectResponse("/admin/dashboard", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="admin_login.html",
        context={"error": "Invalid administrator password.", "user": None}
    )


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Render Admin Control Panel."""
    if not request.session.get("is_admin"):
        return RedirectResponse("/admin/login", status_code=303)

    # Load registry papers
    registry = PaperRegistry()
    all_papers = list(registry.records.values())
    kept_papers = [p for p in all_papers if p.status == "kept"]

    # Count downloaded PDFs
    pdf_count = len(list(settings.research_papers_dir.glob("*.pdf")))

    # Load verified claims
    verified_cache = Path("./data/health_relationships_verified.json")
    verified_claims = []
    if verified_cache.exists():
        try:
            with open(verified_cache, "r", encoding="utf-8") as f:
                verified_claims = json.load(f)
        except Exception:
            verified_claims = []

    # Count ChromaDB embeddings
    total_embeddings = 0
    verified_embeddings = 0
    research_embeddings = 0
    fssai_embeddings = 0
    try:
        vs = VectorStore()
        counts = vs.count()
        research_embeddings = counts.get(COLLECTION_RESEARCH, 0)
        fssai_embeddings = counts.get(COLLECTION_FSSAI, 0)
        verified_embeddings = counts.get(COLLECTION_VERIFIED_RELATIONSHIPS, 0)
        total_embeddings = sum(counts.values())
    except Exception as e:
        logger.debug(f"ChromaDB count error: {e}")

    stats = {
        "total_papers": len(all_papers),
        "kept_papers": len(kept_papers),
        "pdf_count": pdf_count,
        "verified_claims_count": len(verified_claims),
        "embedding_model": settings.ollama_embed_model,
        "total_embeddings": total_embeddings,
        "verified_embeddings": verified_embeddings,
        "research_embeddings": research_embeddings,
        "fssai_embeddings": fssai_embeddings,
    }

    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "stats": stats,
            "papers": all_papers,
            "verified_claims": verified_claims,
            "is_admin": True,
            "user": request.session.get("user")
        }
    )


@app.post("/api/admin/hunter/search")
async def hunter_search(request: Request):
    """Search Europe PMC and arXiv for research paper ideas."""
    if not request.session.get("is_admin"):
        return Response(content=json.dumps({"error": "Unauthorized"}), status_code=401, media_type="application/json")

    query = ""
    limit = 6
    try:
        body = await request.body()
        if body:
            try:
                data = json.loads(body.decode("utf-8"))
                query = data.get("query", "").strip()
                limit = int(data.get("limit", 6))
            except Exception:
                parsed = urllib.parse.parse_qs(body.decode("utf-8", errors="replace"))
                if "query" in parsed:
                    query = parsed["query"][0].strip()
                if "limit" in parsed:
                    limit = int(parsed["limit"][0])
    except Exception as e:
        logger.warning(f"Hunter search body parsing error: {e}")

    if not query:
        return Response(content=json.dumps({"error": "Search query cannot be empty"}), status_code=400, media_type="application/json")

    try:
        search_client = PaperSearchClient()
        papers = search_client.search_all(query=query, limit=limit)
        candidates = [p.model_dump() for p in papers]
        return {
            "status": "success",
            "query": query,
            "total_found": len(candidates),
            "candidates": candidates,
            "notice": getattr(search_client, "last_notice", None)
        }
    except Exception as e:
        logger.error(f"Hunter search error: {e}")
        return Response(content=json.dumps({"error": str(e)}), status_code=500, media_type="application/json")


@app.post("/api/admin/hunter/ingest")
async def hunter_ingest(request: Request):
    """Sequentially download, extract, verify relationships, and index passed claims into vector DB."""
    if not request.session.get("is_admin"):
        return Response(content=json.dumps({"error": "Unauthorized"}), status_code=401, media_type="application/json")

    selected_papers = []
    is_stream = False
    try:
        body = await request.body()
        if body:
            data = json.loads(body.decode("utf-8"))
            selected_papers = data.get("selected_papers", [])
            is_stream = bool(data.get("stream", False)) or "application/x-ndjson" in request.headers.get("accept", "")
    except Exception as e:
        logger.warning(f"Hunter ingest body parsing error: {e}")

    if not selected_papers:
        return Response(content=json.dumps({"error": "No papers selected for ingestion"}), status_code=400, media_type="application/json")

    downloader = PDFDownloader()
    registry = PaperRegistry()
    pipeline = RelationshipPipeline()
    vector_store = VectorStore()

    if is_stream:
        def stream_generator():
            ingested_papers_count = 0
            all_extracted_relationships = []
            new_verified_reports = []
            total_papers = len(selected_papers)

            yield json.dumps({
                "type": "ingest_start",
                "total_papers": total_papers,
                "message": f"Starting ingestion pipeline for {total_papers} selected paper(s)..."
            }) + "\n"

            for p_idx, p in enumerate(selected_papers, 1):
                title = p.get("title", "").strip()
                authors = p.get("authors", "Unknown")
                year = str(p.get("year", "Unknown"))
                doi = p.get("doi")
                pdf_url = p.get("pdf_url")
                abstract = p.get("abstract", "")
                journal = p.get("journal", "Biomedical Journal")

                if not title:
                    continue

                yield json.dumps({
                    "type": "paper_start",
                    "paper_index": p_idx,
                    "total_papers": total_papers,
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "doi": doi,
                    "message": f"Processing paper [{p_idx}/{total_papers}]: '{title[:50]}...'"
                }) + "\n"

                saved_file = None
                # Check if pdf_url is already a local file path
                if pdf_url and Path(pdf_url).exists() and Path(pdf_url).is_file():
                    saved_file = Path(pdf_url)
                    yield json.dumps({
                        "type": "download_verified",
                        "paper_index": p_idx,
                        "saved_path": str(saved_file),
                        "size_kb": saved_file.stat().st_size // 1024,
                        "message": f"Using existing verified manuscript on disk ({saved_file.stat().st_size // 1024} KB)."
                    }) + "\n"
                elif pdf_url:
                    try:
                        for dl_event in downloader.download_stream(
                            pdf_url=pdf_url,
                            title=title,
                            authors=authors,
                            year=year,
                            doi=doi,
                            abstract=abstract,
                            polite_delay=0.1
                        ):
                            dl_event["paper_index"] = p_idx
                            if dl_event.get("type") == "download_result":
                                if dl_event.get("success"):
                                    saved_file = dl_event.get("saved_path")
                            else:
                                yield json.dumps(dl_event) + "\n"
                    except Exception as e:
                        logger.warning(f"Downloader exception for {title}: {e}")
                        yield json.dumps({
                            "type": "warning",
                            "paper_index": p_idx,
                            "message": f"Downloader warning: {e}"
                        }) + "\n"

                # If download didn't save or no pdf_url, write manuscript markdown summary
                if not saved_file or not saved_file.exists():
                    first_author = authors.split(",")[0].split()[0] if authors else "Author"
                    safe_author = downloader._sanitize_filename(first_author)
                    safe_title = downloader._sanitize_filename(title)
                    safe_year = downloader._sanitize_filename(year)
                    md_path = downloader.target_dir / f"{safe_year}_{safe_author}_{safe_title}.md"
                    downloader._write_summary_md(
                        md_path=md_path,
                        title=title,
                        authors=authors,
                        year=year,
                        doi=doi,
                        url=pdf_url or ("https://doi.org/" + doi if doi else ""),
                        abstract=abstract
                    )
                    saved_file = md_path
                    yield json.dumps({
                        "type": "download_fallback",
                        "paper_index": p_idx,
                        "saved_path": str(md_path),
                        "message": f"Generated structured companion markdown summary for analysis."
                    }) + "\n"

                # Register in PaperRegistry
                registry.register(
                    paper_id=p.get("paper_id") or (doi if doi else title[:30]),
                    title=title,
                    status="kept",
                    authors=authors,
                    year=year,
                    journal=journal,
                    doi=doi,
                    abstract=abstract,
                    pdf_url=pdf_url,
                    pdf_path=str(saved_file) if saved_file else None
                )
                ingested_papers_count += 1

                # Process file through extraction and 4-Phase verification pipeline stream
                try:
                    for pipe_event in pipeline.process_paper_stream(saved_file, print_to_terminal=False):
                        pipe_event["paper_index"] = p_idx
                        pipe_event["title"] = title
                        if pipe_event.get("type") == "claim_verified":
                            c = pipe_event.get("claim", {})
                            all_extracted_relationships.append(c)
                        elif pipe_event.get("type") == "report_complete":
                            vrs = pipe_event.get("verified_reports", [])
                            new_verified_reports.extend(vrs)
                        yield json.dumps(pipe_event) + "\n"
                except Exception as e:
                    logger.warning(f"Pipeline verification error on {saved_file}: {e}")
                    yield json.dumps({
                        "type": "warning",
                        "paper_index": p_idx,
                        "message": f"Verification pipeline error on {title}: {e}"
                    }) + "\n"

            # Save to verified cache and index passed relationships in ChromaDB
            yield json.dumps({
                "type": "indexing_start",
                "message": f"Auditing complete: Indexing {len(new_verified_reports)} verified relationships into ChromaDB..."
            }) + "\n"

            passed_count = 0
            if new_verified_reports:
                pipeline._save_verified_cache(new_verified_reports)
                passed_count = vector_store.add_verified_relationships(new_verified_reports)

            counts = vector_store.count()
            total_embeddings = sum(counts.values())
            verified_embeddings = counts.get(COLLECTION_VERIFIED_RELATIONSHIPS, 0)

            yield json.dumps({
                "type": "complete",
                "status": "success",
                "processed_papers_count": ingested_papers_count,
                "new_relationships_verified": len(new_verified_reports),
                "passed_relationships_indexed": passed_count,
                "total_embeddings_in_db": total_embeddings,
                "verified_embeddings_in_db": verified_embeddings,
                "results": all_extracted_relationships,
                "message": f"Ingestion complete: verified {len(new_verified_reports)} claims, indexed {passed_count} high-confidence relationships into ChromaDB!"
            }) + "\n"

        return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

    # Non-streaming fallback for standard HTTP clients / tests
    ingested_papers_count = 0
    all_extracted_relationships = []
    new_verified_reports = []

    for p in selected_papers:
        title = p.get("title", "").strip()
        authors = p.get("authors", "Unknown")
        year = str(p.get("year", "Unknown"))
        doi = p.get("doi")
        pdf_url = p.get("pdf_url")
        abstract = p.get("abstract", "")
        journal = p.get("journal", "Biomedical Journal")

        if not title:
            continue

        saved_file = None
        # Check if pdf_url is already a local file path
        if pdf_url and Path(pdf_url).exists() and Path(pdf_url).is_file():
            saved_file = Path(pdf_url)
        elif pdf_url:
            try:
                success, saved_file, msg = downloader.download(
                    pdf_url=pdf_url,
                    title=title,
                    authors=authors,
                    year=year,
                    doi=doi,
                    abstract=abstract,
                    polite_delay=0.1
                )
            except Exception as e:
                logger.warning(f"Downloader exception for {title}: {e}")

        # If download didn't save or no pdf_url, write manuscript markdown summary
        if not saved_file or not saved_file.exists():
            first_author = authors.split(",")[0].split()[0] if authors else "Author"
            safe_author = downloader._sanitize_filename(first_author)
            safe_title = downloader._sanitize_filename(title)
            safe_year = downloader._sanitize_filename(year)
            md_path = downloader.target_dir / f"{safe_year}_{safe_author}_{safe_title}.md"
            downloader._write_summary_md(
                md_path=md_path,
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                url=pdf_url or ("https://doi.org/" + doi if doi else ""),
                abstract=abstract
            )
            saved_file = md_path

        # Register in PaperRegistry
        registry.register(
            paper_id=p.get("paper_id") or (doi if doi else title[:30]),
            title=title,
            status="kept",
            authors=authors,
            year=year,
            journal=journal,
            doi=doi,
            abstract=abstract,
            pdf_url=pdf_url,
            pdf_path=str(saved_file) if saved_file else None
        )
        ingested_papers_count += 1

        # Process file through extraction and 4-Phase verification pipeline
        try:
            report = pipeline.process_paper_file(saved_file, print_to_terminal=False)
            if report and getattr(report, "verified_reports", None):
                for vr in report.verified_reports:
                    new_verified_reports.append(vr)
                    sub = ""
                    rel_type = ""
                    obj = ""
                    quote = ""
                    if getattr(vr, "relationship", None):
                        sub = vr.relationship.subject
                        rel_type = vr.relationship.relation
                        obj = vr.relationship.object
                        quote = getattr(vr.relationship, "evidence_quote", "")
                    else:
                        sub = getattr(vr, "subject", "")
                        rel_type = getattr(vr, "relation", "")
                        obj = getattr(vr, "object", "")
                        quote = getattr(vr, "evidence_quote", "")
                    
                    if not sub and vr.claim_summary:
                        parts = vr.claim_summary.split(" -> ")
                        sub = parts[0] if len(parts) >= 1 else ""
                        rel_type = parts[1] if len(parts) >= 2 else ""
                        obj = parts[2] if len(parts) >= 3 else ""

                    all_extracted_relationships.append({
                        "paper_title": title,
                        "authors": authors,
                        "year": year,
                        "doi": doi,
                        "claim_summary": vr.claim_summary,
                        "subject": sub,
                        "relation": rel_type,
                        "object": obj,
                        "study_design": vr.study_design.design_type.value if vr.study_design else "Observational",
                        "risk_of_bias": vr.risk_of_bias.level.value if vr.risk_of_bias else "LOW",
                        "nli_status": vr.nli_result.status.value if vr.nli_result else "PASS",
                        "composite_score": vr.final_score,
                        "gating_status": vr.gating_status.value if hasattr(vr.gating_status, "value") else str(vr.gating_status),
                        "evidence_quote": quote
                    })
        except Exception as e:
            logger.warning(f"Pipeline verification error on {saved_file}: {e}")

    # Save to verified cache and index passed relationships in ChromaDB
    passed_count = 0
    if new_verified_reports:
        pipeline._save_verified_cache(new_verified_reports)
        passed_count = vector_store.add_verified_relationships(new_verified_reports)

    # Get updated ChromaDB counts
    counts = vector_store.count()
    total_embeddings = sum(counts.values())
    verified_embeddings = counts.get(COLLECTION_VERIFIED_RELATIONSHIPS, 0)

    return {
        "status": "success",
        "processed_papers_count": ingested_papers_count,
        "new_relationships_verified": len(new_verified_reports),
        "passed_relationships_indexed": passed_count,
        "total_embeddings_in_db": total_embeddings,
        "verified_embeddings_in_db": verified_embeddings,
        "results": all_extracted_relationships
    }


@app.get("/logout")
async def logout(request: Request):
    """Clear session and redirect home."""
    request.session.clear()
    return RedirectResponse("/", status_code=303)
