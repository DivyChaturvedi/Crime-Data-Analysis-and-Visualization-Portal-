import json
import uuid
from pathlib import Path
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User

try:
    from shapely.geometry import Point, shape
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False


class CrimeRecord(models.Model):

    CRIME_TYPES = [
        ('theft', 'Theft'),
        ('assault', 'Assault'),
        ('robbery', 'Robbery'),
        ('murder', 'Murder'),
        ('fraud', 'Fraud & Cybercrime'),
        ('vandalism', 'Vandalism'),
        ('drug_offense', 'Drug Offense'),
        ('burglary', 'Burglary & Break-in'),
        ('harassment', 'Harassment & Stalking'),
        ('vehicle_theft', 'Vehicle Theft'),
        ('other', 'Other Incident'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('approved', 'Verified & Registered'),
        ('investigating', 'Under Active Investigation'),
        ('resolved', 'Case Solved / Closed'),
        ('rejected', 'Rejected / Invalid'),
    ]

    SEVERITY_CHOICES = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    ]

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('undisclosed', 'Prefer not to say'),
    ]

    AGE_GROUP_CHOICES = [
        ('juvenile', 'Under 18 (Juvenile)'),
        ('young_adult', '18 - 29 years'),
        ('adult', '30 - 50 years'),
        ('senior', 'Above 50 years'),
        ('unknown', 'Unknown'),
    ]

    fir_number = models.CharField(
        max_length=40,
        blank=True,
        help_text="Official Police FIR / Case Tracking Number"
    )

    crime_type = models.CharField(
        max_length=30,
        choices=CRIME_TYPES,
        default='theft'
    )

    severity_level = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='medium'
    )

    description = models.TextField(
        help_text="Detailed narrative of the incident"
    )

    location_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Area, street name, or landmark"
    )

    landmark = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Nearest identifiable landmark"
    )

    police_station = models.CharField(
        max_length=150,
        blank=True,
        default='Khargone City Police Station',
        help_text="Jurisdiction police station handling this FIR"
    )

    latitude = models.FloatField()
    longitude = models.FloatField()

    # Original submission timestamp (kept for backward compatibility)
    date_time = models.DateTimeField(default=timezone.now)

    # Actual occurrence datetime
    incident_datetime = models.DateTimeField(
        default=timezone.now,
        help_text="Actual date and time when the crime occurred"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    reported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reported_crimes'
    )

    investigating_officer = models.CharField(
        max_length=150,
        blank=True,
        default='',
        help_text="Assigned IO / Detective name"
    )

    victim_gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        default='undisclosed',
        blank=True
    )

    victim_age_group = models.CharField(
        max_length=20,
        choices=AGE_GROUP_CHOICES,
        default='unknown',
        blank=True
    )

    weapon_involved = models.CharField(
        max_length=100,
        blank=True,
        default='None',
        help_text="E.g. Firearm, Knife, Blunt Instrument, None"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    admin_remark = models.TextField(
        blank=True,
        null=True,
        help_text="Internal police / admin case notes"
    )

    proof_file = models.FileField(
        upload_to='proofs/',
        blank=True,
        null=True,
        help_text="Supporting evidence, FIR photo, or complaint PDF"
    )

    class Meta:
        ordering = ['-incident_datetime', '-date_time']

    def clean(self):
        if self.latitude is None or self.longitude is None:
            raise ValidationError("Latitude & Longitude are required.")

        if not (-90 <= self.latitude <= 90):
            raise ValidationError("Invalid latitude. Must be between -90 and 90.")

        if not (-180 <= self.longitude <= 180):
            raise ValidationError("Invalid longitude. Must be between -180 and 180.")

    def save(self, *args, **kwargs):
        if not self.fir_number:
            dt = self.incident_datetime or self.date_time or timezone.now()
            self.fir_number = f"FIR-{dt.strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
        if not self.incident_datetime and self.date_time:
            self.incident_datetime = self.date_time
        super().save(*args, **kwargs)

    def is_inside_khargone(self):
        """Helper to determine if coordinates fall within Khargone district GeoJSON boundary."""
        if not HAS_SHAPELY:
            return True
        geojson_path = Path(settings.BASE_DIR) / 'static' / 'maps' / 'khargone.geojson'
        if geojson_path.exists():
            try:
                with open(geojson_path, encoding='utf-8') as f:
                    geojson = json.load(f)
                polygon = shape(geojson['features'][0]['geometry'])
                point = Point(self.longitude, self.latitude)
                return polygon.contains(point)
            except Exception:
                return True
        return True

    @property
    def is_active_case(self):
        return self.status in ['pending', 'approved', 'investigating']

    def __str__(self):
        return f"[{self.fir_number}] {self.get_crime_type_display()} @ {self.location_name}"


class CrimeAlert(models.Model):
    ALERT_TYPES = [
        ('warning', 'Security Warning'),
        ('high_risk', 'High-Risk Hotspot Advisory'),
        ('patrol', 'Patrol Dispatch Notice'),
        ('emergency', 'Emergency Broadcast'),
    ]

    SEVERITY_LEVELS = [
        ('info', 'Informational'),
        ('warning', 'Moderate Warning'),
        ('danger', 'Critical Danger'),
    ]

    title = models.CharField(max_length=200)
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES, default='warning')
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='warning')
    message = models.TextField()
    location_name = models.CharField(max_length=255, blank=True, help_text="Target zone or neighborhood")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_alert_type_display()}] {self.title}"


class PatrolSchedule(models.Model):
    SHIFT_CHOICES = [
        ('morning', 'Morning Shift (06:00 - 14:00)'),
        ('evening', 'Evening Shift (14:00 - 22:00)'),
        ('night', 'Night Shift (22:00 - 06:00)'),
    ]

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('active', 'Active on Patrol'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    unit_name = models.CharField(max_length=100, help_text="E.g. PCR Unit 03, Khargone Sector Alpha")
    assigned_area = models.CharField(max_length=200, help_text="Patrol sector or hotspot")
    shift = models.CharField(max_length=20, choices=SHIFT_CHOICES, default='night')
    patrol_date = models.DateField(default=timezone.now)
    officer_in_charge = models.CharField(max_length=150)
    contact_number = models.CharField(max_length=30, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-patrol_date', '-created_at']

    def __str__(self):
        return f"{self.unit_name} - {self.assigned_area} ({self.get_shift_display()})"


class MLPredictionLog(models.Model):
    query_location = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    query_time = models.DateTimeField(default=timezone.now)
    predicted_crime_type = models.CharField(max_length=50)
    predicted_severity = models.CharField(max_length=20)
    risk_score = models.FloatField(default=0.0)  # 0 to 100
    confidence_score = models.FloatField(default=0.0)  # 0.0 to 1.0
    recommendations = models.TextField(blank=True)
    queried_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Prediction for {self.query_location}: {self.risk_score:.1f}% Risk ({self.predicted_crime_type})"