from django.contrib import admin
from .models import CrimeRecord, CrimeAlert, PatrolSchedule, MLPredictionLog


@admin.register(CrimeRecord)
class CrimeRecordAdmin(admin.ModelAdmin):
    list_display = [
        'fir_number',
        'crime_type',
        'severity_level',
        'location_name',
        'reported_by',
        'status',
        'incident_datetime',
    ]
    list_filter = [
        'crime_type',
        'severity_level',
        'status',
        'police_station',
        'incident_datetime',
    ]
    search_fields = [
        'fir_number',
        'location_name',
        'landmark',
        'description',
        'reported_by__username',
    ]
    date_hierarchy = 'incident_datetime'
    actions = ['approve_crimes', 'investigate_crimes', 'resolve_crimes', 'reject_crimes']

    def approve_crimes(self, request, queryset):
        queryset.update(status='approved')
    approve_crimes.short_description = "Verify & Approve selected FIRs"

    def investigate_crimes(self, request, queryset):
        queryset.update(status='investigating')
    investigate_crimes.short_description = "Mark selected FIRs as Under Active Investigation"

    def resolve_crimes(self, request, queryset):
        queryset.update(status='resolved')
    resolve_crimes.short_description = "Mark selected FIRs as Solved / Closed"

    def reject_crimes(self, request, queryset):
        queryset.update(status='rejected')
    reject_crimes.short_description = "Reject selected reports"


@admin.register(CrimeAlert)
class CrimeAlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'alert_type', 'severity', 'location_name', 'is_active', 'created_at']
    list_filter = ['alert_type', 'severity', 'is_active', 'created_at']
    search_fields = ['title', 'message', 'location_name']


@admin.register(PatrolSchedule)
class PatrolScheduleAdmin(admin.ModelAdmin):
    list_display = ['unit_name', 'assigned_area', 'shift', 'patrol_date', 'officer_in_charge', 'status']
    list_filter = ['shift', 'status', 'patrol_date']
    search_fields = ['unit_name', 'assigned_area', 'officer_in_charge']


@admin.register(MLPredictionLog)
class MLPredictionLogAdmin(admin.ModelAdmin):
    list_display = ['query_location', 'predicted_crime_type', 'predicted_severity', 'risk_score', 'queried_by', 'created_at']
    list_filter = ['predicted_crime_type', 'predicted_severity', 'created_at']
    search_fields = ['query_location', 'predicted_crime_type']