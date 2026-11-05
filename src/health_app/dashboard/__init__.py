"""Dashboard package for VITA Health App.

Provides:
- Google OAuth2 authentication
- Google Fitness REST API client (steps, heart rate, sleep)
- Evidence-grounded biometric advisor
- Modern web application on Port 8001
"""

from health_app.dashboard.app import app
from health_app.dashboard.auth import GoogleOAuthManager
from health_app.dashboard.google_health import GoogleFitnessClient, UserHealthData
from health_app.dashboard.biometric_advisor import BiometricAdvisor, BiometricInsight

__all__ = [
    "app",
    "GoogleOAuthManager",
    "GoogleFitnessClient",
    "UserHealthData",
    "BiometricAdvisor",
    "BiometricInsight",
]
