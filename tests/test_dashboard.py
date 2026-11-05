import pytest
from starlette.testclient import TestClient

from health_app.config import settings
from health_app.dashboard.app import app
from health_app.dashboard.auth import GoogleOAuthManager, FITNESS_SCOPES
from health_app.dashboard.google_health import (
    UserHealthData,
    DailySteps,
    DailyRecord,
    HeartRateSummary,
    SleepSummary,
    DailySleepRecord,
    resolve_user_timezone,
    generate_demo_history,
    generate_demo_weekly_sleep,
    save_user_history_cache,
    load_user_history_cache,
    GoogleFitnessClient,
)
from health_app.dashboard.biometric_advisor import BiometricAdvisor


@pytest.fixture
def client():
    return TestClient(app)


def test_oauth_manager_credentials_discovery():
    oauth = GoogleOAuthManager()
    assert oauth.configured is True
    assert oauth.client_id is not None
    assert "1059027165335" in oauth.client_id
    assert str(settings.dashboard_port) in oauth.redirect_uri


def test_oauth_authorization_url_generation():
    oauth = GoogleOAuthManager()
    auth_url = oauth.get_authorization_url(state="test_state_123")
    assert "accounts.google.com" in auth_url
    assert f"client_id={oauth.client_id}" in auth_url
    assert "fitness.activity.read" in auth_url
    assert "fitness.heart_rate.read" in auth_url
    assert "fitness.sleep.read" in auth_url
    assert "state=test_state_123" in auth_url
    assert "prompt=select_account" in auth_url

    # Check force_consent parameter
    forced_url = oauth.get_authorization_url(state="test_state_123", force_consent=True)
    assert "prompt=consent" in forced_url


def test_user_health_data_models():
    data = UserHealthData(
        user_name="John Doe",
        user_email="john@example.com",
        user_picture="https://example.com/avatar.jpg",
        today_steps=9200,
        weekly_steps=[DailySteps(date="Mon", steps=8500)],
        heart_rate=HeartRateSummary(resting_bpm=65, latest_bpm=70),
        sleep=SleepSummary(total_hours=7.5, deep_sleep_hours=2.0, rem_sleep_hours=1.8, sleep_score=88)
    )
    assert data.today_steps == 9200
    assert data.heart_rate.resting_bpm == 65
    assert data.sleep.sleep_score == 88


def test_biometric_advisor_cardiovascular_strain():
    # Simulate short sleep + high resting heart rate
    health = UserHealthData(
        user_name="Test User",
        user_email="test@example.com",
        user_picture="",
        today_steps=4200,
        heart_rate=HeartRateSummary(resting_bpm=82),
        sleep=SleepSummary(total_hours=5.8, deep_sleep_hours=1.0, sleep_score=60)
    )
    insights = BiometricAdvisor.generate_grounded_insights(health)
    assert len(insights) >= 2
    # Check that short sleep + elevated HR triggers warning
    sleep_insight = next(i for i in insights if "Sleep" in i.category)
    assert sleep_insight.status_level == "warning"
    assert "Elevated Resting Heart Rate" in sleep_insight.title
    assert sleep_insight.doi is not None


def test_biometric_advisor_optimal_activity():
    # Simulate high step count + adequate sleep
    health = UserHealthData(
        user_name="Fit User",
        user_email="fit@example.com",
        user_picture="",
        today_steps=10500,
        heart_rate=HeartRateSummary(resting_bpm=62),
        sleep=SleepSummary(total_hours=7.8, sleep_score=90)
    )
    insights = BiometricAdvisor.generate_grounded_insights(health)
    step_insight = next(i for i in insights if "Physical Activity" in i.category)
    assert step_insight.status_level == "optimal"
    assert "Protective" in step_insight.title


def test_landing_page_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "VITA" in response.text
    assert "Sign in with Google" in response.text
    assert "Admin Account" in response.text


def test_google_login_redirect(client):
    response = client.get("/api/auth/google/login", follow_redirects=False)
    # Should redirect to Google's OAuth consent screen
    assert response.status_code in [302, 303, 307]
    assert "accounts.google.com" in response.headers["location"]


def test_dashboard_endpoint_rendering(client):
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "My Health Dashboard" in response.text
    assert "Today's Steps" in response.text
    assert "Resting Heart Rate" in response.text
    assert "Nocturnal Sleep" in response.text
    assert "Evidence-Based Clinical Health Insights" in response.text


def test_admin_auth_flow(client):
    # 1. Unauthenticated admin dashboard access redirects to login
    resp = client.get("/admin/dashboard", follow_redirects=False)
    assert resp.status_code in [302, 303]
    assert "/admin/login" in resp.headers["location"]

    # 2. Invalid password shows error
    resp_bad = client.post("/admin/login", data={"password": "wrongpassword"})
    assert resp_bad.status_code == 200
    assert "Invalid administrator password" in resp_bad.text

    # 3. Valid password logs in and redirects
    resp_good = client.post("/admin/login", data={"password": settings.admin_password}, follow_redirects=False)
    assert resp_good.status_code in [302, 303]
    assert "/admin/dashboard" in resp_good.headers["location"]


def test_daily_record_model_validation():
    rec = DailyRecord(
        date="2026-11-02",
        formatted_date="Nov 02",
        day_name="Mon",
        steps=11042,
        goal_met=True,
        heart_rate_bpm=72,
        sleep_hours=7.4
    )
    assert rec.steps == 11042
    assert rec.goal_met is True
    assert rec.formatted_date == "Nov 02"


def test_timezone_resolution_ist():
    from datetime import timedelta
    # In JS, India Standard Time returns -330
    tz = resolve_user_timezone(tz_offset_minutes=-330)
    assert tz.utcoffset(None) == timedelta(hours=5, minutes=30)


def test_generate_demo_history_180_days():
    tz = resolve_user_timezone(tz_offset_minutes=-330)
    history = generate_demo_history(tz, days=180)
    assert len(history) == 180
    today_rec = history[-1]
    assert today_rec.steps == 11240
    assert today_rec.goal_met is True
    assert history[0].date < history[-1].date


def test_user_cache_save_and_load(tmp_path, monkeypatch):
    import health_app.dashboard.google_health as gh
    monkeypatch.setattr(gh, "CACHE_DIR", tmp_path)

    test_email = "test_user_cache@example.com"
    records = [
        DailyRecord(date="2026-11-01", formatted_date="Nov 01", day_name="Sun", steps=9500),
        DailyRecord(date="2026-11-02", formatted_date="Nov 02", day_name="Mon", steps=11042, goal_met=True)
    ]
    save_user_history_cache(test_email, records)

    loaded = load_user_history_cache(test_email)
    assert len(loaded) == 2
    assert loaded[0].date == "2026-11-01"
    assert loaded[1].steps == 11042
    assert loaded[1].goal_met is True


def test_dashboard_renders_health_app_features(client):
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Physical Movement &amp; Step History" in response.text or "Physical Movement & Step History" in response.text
    assert "tab-7" in response.text
    assert "tab-30" in response.text
    assert "tab-90" in response.text
    assert "tab-180" in response.text
    assert "historicalStepsChart" in response.text
    assert "historyLogList" in response.text
    assert "historyData" in response.text


def test_today_steps_multi_stream_resolution(monkeypatch):
    class MockResponse:
        def __init__(self, step_val):
            self.status_code = 200
            self._val = step_val

        def json(self):
            return {
                "bucket": [{
                    "dataset": [{
                        "point": [{
                            "value": [{"intVal": self._val}]
                        }]
                    }]
                }]
            }

    # Simulate: estimated_steps has 7500, but merge_step_deltas has 11240 (wearable steps)
    def mock_post(url, headers, json, timeout):
        agg = json.get("aggregateBy", [{}])[0]
        src = agg.get("dataSourceId", "")
        if "estimated_steps" in src:
            return MockResponse(7500)
        elif "merge_step_deltas" in src:
            return MockResponse(11240)
        return MockResponse(0)

    import requests
    monkeypatch.setattr(requests, "post", mock_post)

    tz = resolve_user_timezone(tz_offset_minutes=-330)
    client = GoogleFitnessClient(access_token="fake_token")
    today_steps = client._fetch_today_steps(tz)

    # Must pick the true maximum (11240) rather than underreporting 7500!
    assert today_steps == 11240


def test_quick_health_data_fast_sync(monkeypatch):
    class MockResponse:
        def __init__(self, val=8000):
            self.status_code = 200
            self._val = val

        def json(self):
            return {
                "bucket": [{
                    "startTimeMillis": "1730505600000",
                    "dataset": [{
                        "point": [{"value": [{"intVal": self._val, "fpVal": 72.0}]}]
                    }]
                }]
            }

    import requests
    monkeypatch.setattr(requests, "post", lambda *a, **k: MockResponse(9500))

    fit_client = GoogleFitnessClient(access_token="fake_token")
    profile = {"name": "Test User", "email": "test@quick.com", "picture": ""}
    data = fit_client.fetch_quick_health_data(profile, tz_offset_minutes=-330)

    assert data.today_steps == 9500
    assert len(data.weekly_steps) > 0
    assert data.is_live_data is True


def test_sync_history_endpoint_unauthenticated(client):
    response = client.post("/api/health/sync-history")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unauthenticated"


def test_oauth_callback_instant_redirect(client, monkeypatch, tmp_path):
    from health_app.dashboard.auth import GoogleOAuthManager
    from health_app.dashboard import user_profile

    monkeypatch.setattr(user_profile, "USER_PROFILES_DIR", tmp_path)
    monkeypatch.setattr(GoogleOAuthManager, "exchange_code_for_tokens", lambda self, c: {"access_token": "mock_token_abc"})
    monkeypatch.setattr(GoogleOAuthManager, "get_user_profile", lambda self, t: {"name": "Instant User", "email": "instant@test.com", "picture": ""})

    # 1. New user without profile redirects immediately to /onboarding
    response = client.get("/api/auth/google/callback?code=mock_valid_code", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/onboarding"

    # 2. Existing user with completed onboarding redirects directly to /dashboard
    user_profile.save_user_profile("instant@test.com", user_profile.UserLifestyleProfile(email="instant@test.com", onboarding_completed=True))
    response_existing = client.get("/api/auth/google/callback?code=mock_valid_code", follow_redirects=False)
    assert response_existing.status_code == 303
    assert response_existing.headers["location"] == "/dashboard"


def test_sleep_summary_and_daily_record_models():
    rec = DailySleepRecord(
        date="2026-11-02",
        formatted_date="Nov 02",
        day_name="Mon",
        total_hours=3.5,
        formatted_duration="3h 27m",
        deep_sleep_hours=0.6,
        rem_sleep_hours=0.7,
        light_sleep_hours=2.0,
        awake_hours=0.2,
        sleep_score=44
    )
    assert rec.formatted_duration == "3h 27m"
    assert rec.total_hours == 3.5

    summary = SleepSummary(
        total_hours=3.5,
        formatted_duration="3h 27m",
        deep_sleep_hours=0.6,
        rem_sleep_hours=0.7,
        light_sleep_hours=2.0,
        awake_hours=0.2,
        sleep_score=44,
        weekly_sleep=[rec]
    )
    assert summary.formatted_duration == "3h 27m"
    assert len(summary.weekly_sleep) == 1
    assert summary.weekly_sleep[0].total_hours == 3.5


def test_generate_demo_weekly_sleep():
    tz = resolve_user_timezone(-330)
    sleep_summary = generate_demo_weekly_sleep(tz)

    assert len(sleep_summary.weekly_sleep) == 7
    # Last night record matches user's 3h 27m
    last_night = sleep_summary.weekly_sleep[-1]
    assert last_night.formatted_duration == "3h 27m"
    assert last_night.total_hours == 3.5
    assert sleep_summary.total_hours == 3.5
    assert sleep_summary.formatted_duration == "3h 27m"
    assert sleep_summary.deep_sleep_hours == 0.6
    assert sleep_summary.rem_sleep_hours == 0.7
    assert sleep_summary.awake_hours == 0.2


def test_sleep_stage_parsing_from_segments(monkeypatch):
    """Test com.google.sleep.segment integer stage codes parsing."""
    import requests
    from datetime import datetime, timezone

    # Simulate Google Fit dataset:aggregate response with stage points:
    # 5 = Deep Sleep (3600s = 1.0h)
    # 6 = REM Sleep (2700s = 0.75h)
    # 4 = Light Sleep (5400s = 1.5h)
    # 1 = Awake (720s = 0.2h)
    class MockAggregateResponse:
        def __init__(self):
            self.status_code = 200

        def json(self):
            return {
                "bucket": [{
                    "dataset": [{
                        "point": [
                            # Deep sleep: 1 hour (3.6e12 ns)
                            {
                                "startTimeNanos": "1730510000000000000",
                                "endTimeNanos": "1730513600000000000",
                                "value": [{"intVal": 5}]
                            },
                            # REM sleep: 45 min = 2700s (2.7e12 ns)
                            {
                                "startTimeNanos": "1730513600000000000",
                                "endTimeNanos": "1730516300000000000",
                                "value": [{"intVal": 6}]
                            },
                            # Light sleep: 1.5 hours = 5400s (5.4e12 ns)
                            {
                                "startTimeNanos": "1730516300000000000",
                                "endTimeNanos": "1730521700000000000",
                                "value": [{"intVal": 4}]
                            },
                            # Awake: 12 min = 720s (0.72e12 ns)
                            {
                                "startTimeNanos": "1730521700000000000",
                                "endTimeNanos": "1730522420000000000",
                                "value": [{"intVal": 1}]
                            }
                        ]
                    }]
                }]
            }

    monkeypatch.setattr(requests, "post", lambda *a, **k: MockAggregateResponse())

    client = GoogleFitnessClient(access_token="fake_token")
    deep_h, rem_h, light_h, awake_h = client._query_session_stages(1730510000000, 1730522420000)

    assert deep_h == 1.0
    assert rem_h == 0.8  # round(2700 / 3600, 1) = 0.75 -> 0.8
    assert light_h == 1.5
    assert awake_h == 0.2


def test_process_sleep_sessions_groups_and_isolates_latest():
    """Test that multiple sessions across 7 days are grouped by calendar day and the latest night sets the summary duration."""
    tz = resolve_user_timezone(-330)
    client = GoogleFitnessClient(access_token="fake_token")

    from datetime import datetime, timedelta
    now_local = datetime.now(tz)

    # 3 sessions ending on 3 consecutive days:
    # 2 days ago: ended 2 days ago at 06:00 AM (7 hours)
    two_days_ago_end = (now_local - timedelta(days=2)).replace(hour=6, minute=0, second=0)
    two_days_ago_start = two_days_ago_end - timedelta(hours=7)

    # Yesterday: ended yesterday at 06:30 AM (6.5 hours)
    yesterday_end = (now_local - timedelta(days=1)).replace(hour=6, minute=30, second=0)
    yesterday_start = yesterday_end - timedelta(hours=6, minutes=30)

    # Last night: ended today at 04:27 AM (3 hours 27 min = 3.5 hours)
    last_night_end = now_local.replace(hour=4, minute=27, second=0)
    last_night_start = last_night_end - timedelta(hours=3, minutes=27)

    raw_sessions = [
        {
            "id": "session_1",
            "startTimeMillis": str(int(two_days_ago_start.timestamp() * 1000)),
            "endTimeMillis": str(int(two_days_ago_end.timestamp() * 1000)),
            "activityType": 72
        },
        {
            "id": "session_2",
            "startTimeMillis": str(int(yesterday_start.timestamp() * 1000)),
            "endTimeMillis": str(int(yesterday_end.timestamp() * 1000)),
            "activityType": 72
        },
        {
            "id": "session_3",
            "startTimeMillis": str(int(last_night_start.timestamp() * 1000)),
            "endTimeMillis": str(int(last_night_end.timestamp() * 1000)),
            "activityType": 72
        }
    ]

    summary = client._process_sleep_sessions(
        raw_sessions,
        start_millis=int(two_days_ago_start.timestamp() * 1000),
        end_millis=int(last_night_end.timestamp() * 1000),
        user_tz=tz
    )

    # 1. Total hours on summary MUST be last night's 3.5 hrs (3h 27m), NOT the 7-day sum of 17h!
    assert summary.total_hours == 3.5
    assert summary.formatted_duration == "3h 27m"

    # 2. weekly_sleep has 7 calendar days
    assert len(summary.weekly_sleep) == 7
    # Last entry in weekly_sleep corresponds to last night's session
    assert summary.weekly_sleep[-1].formatted_duration == "3h 27m"
    assert summary.weekly_sleep[-1].total_hours == 3.5


def test_dashboard_sleep_ui_elements(client):
    """Test that dashboard template renders the 7-day sleep chart and last night's architecture."""
    response = client.get("/dashboard?demo=true")
    assert response.status_code == 200
    assert "weeklySleepChart" in response.text
    assert "weeklySleepData" in response.text
    assert "7-Day Sleep Duration Trends" in response.text
    assert "Last Night's Sleep Architecture" in response.text
    assert "3h 27m" in response.text

