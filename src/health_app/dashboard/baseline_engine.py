import math
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MetricBaseline(BaseModel):
    """Statistical baseline parameters and acute anomaly evaluation for a single biometric."""
    metric_name: str  # resting_heart_rate, sleep_duration, step_volume
    metric_label: str  # "Resting Heart Rate", "Nocturnal Sleep", "Daily Step Count"
    unit: str  # "bpm", "hrs", "steps"
    active_days: int
    rolling_mean: float
    std_dev: float
    ewma_mean: float
    lower_bound: float
    upper_bound: float
    acute_value: float
    variance_delta_z: float
    deviation_label: str  # e.g. "+1.8σ (Elevated)", "In Personal Norm"
    is_anomaly: bool
    status_category: str  # "elevated", "deficient", "normal"
    personal_norm_str: str  # e.g. "64 bpm", "7.2 hrs"
    normal_bandwidth_str: str  # e.g. "58 - 70 bpm"
    descriptive_observation: str


class UserBaselineReport(BaseModel):
    """Aggregate personalized baseline report across telemetry biometrics."""
    email: str
    state: str = "calibration_mode"  # "calibration_mode" or "active_calibrated"
    calibration_day: int = 0
    calibration_target: int = 15
    calibration_percentage: int = 0
    suppress_clinical_alarms: bool = True
    heart_rate: Optional[MetricBaseline] = None
    sleep: Optional[MetricBaseline] = None
    steps: Optional[MetricBaseline] = None

    def get_acute_deviations(self) -> List[MetricBaseline]:
        """Return list of metrics currently outside their personal normal bandwidth [μ - 1.5σ, μ + 1.5σ]."""
        anomalies: List[MetricBaseline] = []
        for b in [self.heart_rate, self.sleep, self.steps]:
            if b and b.is_anomaly:
                anomalies.append(b)
        return anomalies


class StatisticalBaselineEngine:
    """15-Day Rolling Statistical Calibration Engine (μ ± 1.5σ) with EWMA Drift Adaptation.
    Operates a strict two-tier state machine:
      - Calibration Mode (< 15 active days): Suppresses premature clinical alarms; outputs descriptive stats.
      - Active Baseline Mode (>= 15 active days): Evaluates acute telemetry strictly against personal norms.
    """

    EWMA_ALPHA = 0.12  # Smoothing factor for gradual physiological adaptation without false alarms
    SIGMA_BAND = 1.5   # Personal operational bandwidth multiplier [μ - 1.5σ, μ + 1.5σ]

    @classmethod
    def compute_metric_baseline(
        cls,
        metric_name: str,
        metric_label: str,
        unit: str,
        values: List[float],
        acute_val: float,
        min_std_dev: float = 0.5
    ) -> MetricBaseline:
        """Calculate personal rolling mean, std dev, EWMA drift mean, and acute Z-score deviation."""
        clean_vals = [float(v) for v in values if v is not None and v > 0]
        n = len(clean_vals)

        if n == 0:
            mean_val = acute_val if acute_val > 0 else 70.0
            std_val = min_std_dev
            ewma_val = mean_val
        elif n == 1:
            mean_val = clean_vals[0]
            std_val = min_std_dev
            ewma_val = mean_val
        else:
            mean_val = sum(clean_vals) / n
            variance = sum((x - mean_val) ** 2 for x in clean_vals) / (n - 1)
            std_val = max(min_std_dev, math.sqrt(variance))

            # Exponentially Weighted Moving Average (EWMA) for drift adaptation
            ewma_val = clean_vals[0]
            for v in clean_vals[1:]:
                ewma_val = cls.EWMA_ALPHA * v + (1.0 - cls.EWMA_ALPHA) * ewma_val

        # Personal operational bandwidth: [μ - 1.5σ, μ + 1.5σ]
        lower_bound = max(0.0, mean_val - cls.SIGMA_BAND * std_val)
        upper_bound = mean_val + cls.SIGMA_BAND * std_val

        # Acute deviation Z-score: (x_acute - μ) / σ
        if std_val > 0:
            z_score = (acute_val - mean_val) / std_val
        else:
            z_score = 0.0

        is_anomaly = False
        if acute_val > upper_bound:
            is_anomaly = True
            status_cat = "elevated"
            dev_label = f"+{abs(z_score):.1f}σ (Elevated)"
            obs = f"{metric_label} of {acute_val:g} {unit} is elevated by +{abs(acute_val - mean_val):.1f} {unit} above your personal norm ({mean_val:.1f} {unit})."
        elif acute_val < lower_bound and acute_val > 0:
            is_anomaly = True
            status_cat = "deficient"
            dev_label = f"-{abs(z_score):.1f}σ (Below Baseline)"
            obs = f"{metric_label} of {acute_val:g} {unit} is -{abs(acute_val - mean_val):.1f} {unit} below your personal baseline ({mean_val:.1f} {unit})."
        else:
            status_cat = "normal"
            sign_str = "+" if z_score >= 0 else "-"
            dev_label = f"{sign_str}{abs(z_score):.1f}σ (In Personal Norm)"
            obs = f"{metric_label} of {acute_val:g} {unit} is within your personal operational bandwidth ({lower_bound:.1f} - {upper_bound:.1f} {unit})."

        return MetricBaseline(
            metric_name=metric_name,
            metric_label=metric_label,
            unit=unit,
            active_days=n,
            rolling_mean=round(mean_val, 1),
            std_dev=round(std_val, 1),
            ewma_mean=round(ewma_val, 1),
            lower_bound=round(lower_bound, 1),
            upper_bound=round(upper_bound, 1),
            acute_value=round(acute_val, 1),
            variance_delta_z=round(z_score, 2),
            deviation_label=dev_label,
            is_anomaly=is_anomaly,
            status_category=status_cat,
            personal_norm_str=f"{round(mean_val, 1)} {unit}",
            normal_bandwidth_str=f"{round(lower_bound, 1)} - {round(upper_bound, 1)} {unit}",
            descriptive_observation=obs
        )

    @classmethod
    def evaluate_user_telemetry(
        cls,
        email: str,
        history_records: List[Any],
        acute_heart_rate: float,
        acute_sleep_hours: float,
        acute_steps: int,
    ) -> UserBaselineReport:
        """Analyze up to 180 days of wearable history, enforce 15-day calibration state machine,
        and construct user baseline report.
        """
        hr_series: List[float] = []
        sleep_series: List[float] = []
        steps_series: List[float] = []

        # Extract numerical arrays from records
        for r in history_records:
            if isinstance(r, dict):
                hr = r.get("heart_rate_bpm") or 0.0
                sl = r.get("sleep_hours") or 0.0
                st = r.get("steps") or 0
            else:
                hr = getattr(r, "heart_rate_bpm", 0.0) or 0.0
                sl = getattr(r, "sleep_hours", 0.0) or 0.0
                st = getattr(r, "steps", 0) or 0

            if hr > 0:
                hr_series.append(float(hr))
            if sl > 0:
                sleep_series.append(float(sl))
            if st > 0:
                steps_series.append(float(st))

        active_days = max(len(hr_series), len(sleep_series), len(steps_series))

        # Two-Tier State Machine
        if active_days < 15:
            state = "calibration_mode"
            suppress_alarms = True
            cal_pct = min(100, int((active_days / 15.0) * 100))
        else:
            state = "active_calibrated"
            suppress_alarms = False
            cal_pct = 100

        # Compute baselines for the 3 primary modalities
        hr_base = cls.compute_metric_baseline(
            metric_name="resting_heart_rate",
            metric_label="Resting Heart Rate",
            unit="bpm",
            values=hr_series,
            acute_val=acute_heart_rate,
            min_std_dev=2.0
        )

        sleep_base = cls.compute_metric_baseline(
            metric_name="sleep_duration",
            metric_label="Nocturnal Sleep",
            unit="hrs",
            values=sleep_series,
            acute_val=acute_sleep_hours,
            min_std_dev=0.4
        )

        steps_base = cls.compute_metric_baseline(
            metric_name="step_volume",
            metric_label="Daily Physical Movement",
            unit="steps",
            values=steps_series,
            acute_val=float(acute_steps),
            min_std_dev=500.0
        )

        return UserBaselineReport(
            email=email,
            state=state,
            calibration_day=active_days,
            calibration_target=15,
            calibration_percentage=cal_pct,
            suppress_clinical_alarms=suppress_alarms,
            heart_rate=hr_base,
            sleep=sleep_base,
            steps=steps_base
        )
