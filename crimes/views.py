import csv
import io
import json
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .analytics import get_dashboard_analytics
from .forms import (
    CrimeAlertForm,
    CrimeRecordForm,
    CSVUploadForm,
    FilterForm,
    MLPredictForm,
    StatusUpdateForm,
)
from .ml_engine import (
    calculate_risk_probability,
    compute_spatial_clusters,
    predict_incident_features,
    train_nlp_models,
)
from .models import CrimeAlert, CrimeRecord, MLPredictionLog, PatrolSchedule
from .reports import generate_bulletin_pdf, generate_fir_pdf


# =========================
# HELPER FUNCTIONS
# =========================
def load_khargone_geojson():
    geojson_path = Path(settings.BASE_DIR) / 'static' / 'maps' / 'khargone.geojson'
    if geojson_path.exists():
        try:
            with open(geojson_path, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def get_time_slot_label(dt):
    if not dt:
        return 'Unknown'
    hour = dt.hour
    if 0 <= hour < 4:
        return '12 AM - 4 AM'
    if 4 <= hour < 8:
        return '4 AM - 8 AM'
    if 8 <= hour < 12:
        return '8 AM - 12 PM'
    if 12 <= hour < 16:
        return '12 PM - 4 PM'
    if 16 <= hour < 20:
        return '4 PM - 8 PM'
    return '8 PM - 12 AM'


def serialize_record(record):
    dt = record.incident_datetime or record.date_time
    return {
        'id': record.id,
        'fir_number': record.fir_number,
        'crime_type': record.crime_type,
        'crime_type_display': record.get_crime_type_display(),
        'severity_level': record.severity_level,
        'severity_display': record.get_severity_level_display(),
        'status': record.status,
        'status_display': record.get_status_display(),
        'latitude': record.latitude,
        'longitude': record.longitude,
        'location_name': record.location_name or 'N/A',
        'landmark': record.landmark or '',
        'police_station': record.police_station or '',
        'description': record.description[:120] + ('...' if len(record.description) > 120 else ''),
        'date_time': dt.strftime('%d %b %Y, %I:%M %p') if dt else '',
        'reported_by': record.reported_by.username if record.reported_by else 'Citizen / Anonymous',
        'time_slot': get_time_slot_label(dt),
        'proof_url': record.proof_file.url if record.proof_file else '',
    }


def is_admin_or_staff(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


# =========================
# DASHBOARD VIEW
# =========================
@login_required
def dashboard(request):
    approved_records = CrimeRecord.objects.filter(status__in=['approved', 'investigating', 'resolved'])
    
    analytics_data = get_dashboard_analytics(approved_records)
    hotspot_clusters = compute_spatial_clusters(approved_records)
    
    # Calculate alert summary counts
    red_count = sum(1 for c in hotspot_clusters if c['alert_level'] == 'red')
    yellow_count = sum(1 for c in hotspot_clusters if c['alert_level'] == 'yellow')
    green_count = sum(1 for c in hotspot_clusters if c['alert_level'] == 'green')
    
    alert_summary = {
        'red_count': red_count,
        'yellow_count': yellow_count,
        'green_count': green_count,
    }

    # Active safety alerts
    active_alerts = CrimeAlert.objects.filter(is_active=True)[:4]
    
    # Recent FIR activity
    recent_crimes = CrimeRecord.objects.all().order_by('-created_at')[:8]

    # Time slot risk counts
    slot_counter = Counter()
    for r in approved_records:
        dt = r.incident_datetime or r.date_time
        slot_counter[get_time_slot_label(dt)] += 1

    risky_time_slots = [{'label': k, 'count': v} for k, v in slot_counter.most_common(6)]

    context = {
        'analytics': analytics_data,
        'analytics_json': json.dumps(analytics_data),
        'hotspot_areas': hotspot_clusters[:6],
        'alert_summary': alert_summary,
        'active_alerts': active_alerts,
        'recent_crimes': recent_crimes,
        'risky_time_slots': risky_time_slots,
    }
    return render(request, 'crimes/dashboard.html', context)


# =========================
# AI & ML INTELLIGENCE HUB
# =========================
@login_required
def ai_analytics_view(request):
    approved_records = CrimeRecord.objects.filter(status__in=['approved', 'investigating', 'resolved'])
    clusters = compute_spatial_clusters(approved_records)
    
    prediction_result = None
    nlp_result = None

    if request.method == 'POST':
        form = MLPredictForm(request.POST)
        if form.is_valid():
            loc_name = form.cleaned_data['location_name']
            lat = form.cleaned_data['latitude']
            lng = form.cleaned_data['longitude']
            t_dt = form.cleaned_data.get('target_datetime') or timezone.now()
            desc = form.cleaned_data.get('incident_description') or ""

            # Run ML risk calculation
            prediction_result = calculate_risk_probability(lat, lng, t_dt, approved_records)
            prediction_result['location_name'] = loc_name
            prediction_result['latitude'] = lat
            prediction_result['longitude'] = lng

            # Run NLP classification if text provided
            if desc:
                nlp_result = predict_incident_features(desc)

            # Log prediction for analytics
            try:
                MLPredictionLog.objects.create(
                    query_location=loc_name,
                    latitude=lat,
                    longitude=lng,
                    query_time=t_dt,
                    predicted_crime_type=nlp_result['predicted_crime_type'] if nlp_result else prediction_result['predicted_primary_threat'],
                    predicted_severity=nlp_result['predicted_severity'] if nlp_result else prediction_result['risk_level'],
                    risk_score=prediction_result['risk_score'],
                    confidence_score=nlp_result['confidence'] if nlp_result else 0.85,
                    recommendations="\n".join(prediction_result['recommendations']),
                    queried_by=request.user
                )
            except Exception:
                pass

            messages.success(request, f"AI Assessment generated: {prediction_result['risk_score']}% Risk Score for {loc_name}")
    else:
        # Default with Khargone Center
        form = MLPredictForm(initial={
            'location_name': 'Khargone City Center',
            'latitude': 21.8247,
            'longitude': 75.6102,
            'target_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M')
        })

    # ML Model metadata & analytics
    analytics_data = get_dashboard_analytics(approved_records)
    prediction_history = MLPredictionLog.objects.all().order_by('-created_at')[:6]

    context = {
        'form': form,
        'prediction_result': prediction_result,
        'nlp_result': nlp_result,
        'clusters': clusters,
        'clusters_json': json.dumps(clusters),
        'analytics': analytics_data,
        'analytics_json': json.dumps(analytics_data),
        'prediction_history': prediction_history,
        'khargone_geojson': json.dumps(load_khargone_geojson()),
    }
    return render(request, 'crimes/ai_analytics.html', context)


# =========================
# ML PREDICT API
# =========================
@login_required
def api_ml_predict(request):
    try:
        lat = float(request.GET.get('lat', 21.8247))
        lng = float(request.GET.get('lng', 75.6102))
        res = calculate_risk_probability(lat, lng)
        return JsonResponse({'status': 'success', 'data': res})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def api_ml_classify_text(request):
    try:
        text = request.GET.get('text', '').strip()
        res = predict_incident_features(text)
        return JsonResponse({'status': 'success', 'data': res})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# =========================
# INTERACTIVE MAP VIEW
# =========================
@login_required
def map_view(request):
    approved_records = CrimeRecord.objects.filter(status__in=['approved', 'investigating', 'resolved'])
    
    serialized = [serialize_record(r) for r in approved_records]
    hotspot_clusters = compute_spatial_clusters(approved_records)
    
    red_count = sum(1 for c in hotspot_clusters if c['alert_level'] == 'red')
    yellow_count = sum(1 for c in hotspot_clusters if c['alert_level'] == 'yellow')
    green_count = sum(1 for c in hotspot_clusters if c['alert_level'] == 'green')
    
    alert_summary = {
        'red_count': red_count,
        'yellow_count': yellow_count,
        'green_count': green_count,
    }

    # Time slot risk counts
    slot_counter = Counter()
    for r in approved_records:
        dt = r.incident_datetime or r.date_time
        slot_counter[get_time_slot_label(dt)] += 1

    risky_time_slots = [{'label': k, 'count': v} for k, v in slot_counter.most_common(5)]

    context = {
        'crimes_json': json.dumps(serialized),
        'map_data': json.dumps(serialized),
        'hotspot_clusters_json': json.dumps(hotspot_clusters),
        'hotspot_areas': hotspot_clusters,
        'hotspot_areas_json': json.dumps(hotspot_clusters),
        'khargone_geojson': json.dumps(load_khargone_geojson()),
        'alert_summary': alert_summary,
        'risky_time_slots': risky_time_slots,
        'crimes_count': approved_records.count(),
        'total_crimes_count': approved_records.count(),
        'crime_types_list': CrimeRecord.CRIME_TYPES,
    }
    return render(request, 'crimes/map.html', context)


# =========================
# CRIME LIST & FILTERS
# =========================
@login_required
def crime_list(request):
    form = FilterForm(request.GET)
    records = CrimeRecord.objects.all()

    if form.is_valid():
        crime_type = form.cleaned_data.get('crime_type')
        severity = form.cleaned_data.get('severity')
        status = form.cleaned_data.get('status')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        search = form.cleaned_data.get('search')

        if crime_type:
            records = records.filter(crime_type=crime_type)
        if severity:
            records = records.filter(severity_level=severity)
        if status:
            records = records.filter(status=status)
        if date_from:
            records = records.filter(Q(incident_datetime__date__gte=date_from) | Q(date_time__date__gte=date_from))
        if date_to:
            records = records.filter(Q(incident_datetime__date__lte=date_to) | Q(date_time__date__lte=date_to))
        if search:
            records = records.filter(
                Q(fir_number__icontains=search) |
                Q(location_name__icontains=search) |
                Q(landmark__icontains=search) |
                Q(description__icontains=search) |
                Q(police_station__icontains=search)
            )

    paginator = Paginator(records, 10)
    page_number = request.GET.get('page')
    crimes = paginator.get_page(page_number)

    context = {
        'crimes': crimes,
        'form': form,
        'total_count': records.count(),
    }
    return render(request, 'crimes/crime_list.html', context)


# =========================
# CRIME DETAIL & FIR TRACKING
# =========================
@login_required
def crime_detail(request, pk):
    crime = get_object_or_404(CrimeRecord, pk=pk)
    status_form = None

    if request.user.is_staff:
        if request.method == 'POST':
            status_form = StatusUpdateForm(request.POST, instance=crime)
            if status_form.is_valid():
                status_form.save()
                messages.success(request, f"FIR #{crime.fir_number} status updated to {crime.get_status_display()}.")
                return redirect('crime_detail', pk=crime.pk)
        else:
            status_form = StatusUpdateForm(instance=crime)

    context = {
        'crime': crime,
        'status_form': status_form,
        'is_owner': (crime.reported_by == request.user or request.user.is_staff),
        'crime_json': json.dumps(serialize_record(crime)),
    }
    return render(request, 'crimes/crime_detail.html', context)


# =========================
# ADD CRIME RECORD
# =========================
@login_required
def crime_add(request):
    if request.method == 'POST':
        form = CrimeRecordForm(request.POST, request.FILES)
        if form.is_valid():
            crime = form.save(commit=False)
            crime.reported_by = request.user
            crime.status = 'approved' if request.user.is_staff else 'pending'

            # Coordinates fallback
            lat = request.POST.get('latitude')
            lng = request.POST.get('longitude')
            if lat and lng:
                crime.latitude = float(lat)
                crime.longitude = float(lng)
            else:
                crime.latitude = 21.8247
                crime.longitude = 75.6102

            # Actual incident date
            inc_dt = form.cleaned_data.get('incident_datetime')
            if inc_dt:
                crime.incident_datetime = inc_dt

            crime.save()
            messages.success(request, f"FIR #{crime.fir_number} submitted successfully for official verification.")
            return redirect('crime_detail', pk=crime.pk)
        else:
            messages.error(request, "Please correct the highlighted form errors below.")
    else:
        form = CrimeRecordForm()

    context = {
        'form': form,
        'action': 'Report / File',
        'khargone_geojson': json.dumps(load_khargone_geojson()),
    }
    return render(request, 'crimes/crime_form.html', context)


# =========================
# EDIT CRIME RECORD
# =========================
@login_required
def crime_edit(request, pk):
    crime = get_object_or_404(CrimeRecord, pk=pk)

    # Permission check: Only original reporter or staff can edit
    if not (request.user.is_staff or crime.reported_by == request.user):
        messages.error(request, "You do not have permission to modify this FIR report.")
        return redirect('crime_list')

    if request.method == 'POST':
        form = CrimeRecordForm(request.POST, request.FILES, instance=crime)
        if form.is_valid():
            updated = form.save(commit=False)
            lat = request.POST.get('latitude')
            lng = request.POST.get('longitude')
            if lat and lng:
                updated.latitude = float(lat)
                updated.longitude = float(lng)

            updated.save()
            messages.success(request, f"FIR #{crime.fir_number} updated successfully.")
            return redirect('crime_detail', pk=crime.pk)
    else:
        form = CrimeRecordForm(instance=crime)

    context = {
        'form': form,
        'crime': crime,
        'action': 'Edit',
        'khargone_geojson': json.dumps(load_khargone_geojson()),
    }
    return render(request, 'crimes/crime_form.html', context)


# =========================
# DELETE CRIME RECORD
# =========================
@login_required
def crime_delete(request, pk):
    crime = get_object_or_404(CrimeRecord, pk=pk)

    if not (request.user.is_staff or crime.reported_by == request.user):
        messages.error(request, "You do not have permission to delete this record.")
        return redirect('crime_list')

    if request.method == 'POST':
        fir_no = crime.fir_number
        crime.delete()
        messages.success(request, f"FIR #{fir_no} removed from database.")
        return redirect('crime_list')

    return render(request, 'crimes/crime_confirm_delete.html', {'crime': crime})


# =========================
# PDF REPORTS
# =========================
@login_required
def download_fir_pdf(request, pk):
    crime = get_object_or_404(CrimeRecord, pk=pk)
    return generate_fir_pdf(crime)


@login_required
def download_bulletin_pdf(request):
    records = CrimeRecord.objects.filter(status__in=['approved', 'investigating', 'resolved'])
    clusters = compute_spatial_clusters(records)
    alert_summary = {
        'red_count': sum(1 for c in clusters if c['alert_level'] == 'red'),
        'yellow_count': sum(1 for c in clusters if c['alert_level'] == 'yellow'),
        'green_count': sum(1 for c in clusters if c['alert_level'] == 'green'),
    }
    return generate_bulletin_pdf(records, alert_summary, clusters)


# =========================
# CSV EXPORT & IMPORT
# =========================
def sanitize_csv_cell(val):
    """
    Sanitizes values against CSV Formula Injection (CWE-1236).
    Prepends a single quote if string begins with dangerous spreadsheet formula triggers.
    """
    if val is None:
        return ''
    s = str(val)
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + s
    return s


@login_required
def csv_export(request):
    records = CrimeRecord.objects.all().order_by('-incident_datetime')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="Crime_Records_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'fir_number', 'crime_type', 'severity_level', 'status', 'location_name',
        'landmark', 'police_station', 'latitude', 'longitude', 'incident_datetime',
        'reported_by', 'investigating_officer', 'description'
    ])
    
    for r in records:
        writer.writerow([
            sanitize_csv_cell(r.fir_number),
            sanitize_csv_cell(r.crime_type),
            sanitize_csv_cell(r.severity_level),
            sanitize_csv_cell(r.status),
            sanitize_csv_cell(r.location_name),
            sanitize_csv_cell(r.landmark),
            sanitize_csv_cell(r.police_station),
            r.latitude,
            r.longitude,
            (r.incident_datetime or r.date_time).strftime('%Y-%m-%d %H:%M:%S'),
            sanitize_csv_cell(r.reported_by.username if r.reported_by else 'N/A'),
            sanitize_csv_cell(r.investigating_officer),
            sanitize_csv_cell(r.description.replace('\n', ' '))
        ])
    return response


@login_required
def csv_upload(request):
    if not request.user.is_staff:
        messages.error(request, "Only police officers and administrators can upload bulk datasets.")
        return redirect('crime_list')

    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            try:
                data = csv_file.read().decode('utf-8-sig')
                io_string = io.StringIO(data)
                reader = csv.DictReader(io_string)
                reader.fieldnames = [f.strip().lower() for f in reader.fieldnames if f]

                imported_count = 0
                error_count = 0
                max_rows = 5000  # DoS Prevention: limit batch import to 5,000 rows

                for i, row in enumerate(reader):
                    if i >= max_rows:
                        messages.warning(request, f"Import capped at {max_rows} rows for server stability.")
                        break
                    try:
                        c_type = row.get('crime_type', 'other').strip().lower()
                        loc = row.get('location_name', '').strip()
                        lat = float(row.get('latitude', 21.8247))
                        lng = float(row.get('longitude', 75.6102))
                        desc = row.get('description', '').strip()
                        sev = row.get('severity_level', 'medium').strip().lower()
                        if sev not in ['low', 'medium', 'high', 'critical']:
                            sev = 'medium'

                        CrimeRecord.objects.create(
                            crime_type=c_type,
                            severity_level=sev,
                            location_name=loc,
                            latitude=lat,
                            longitude=lng,
                            description=desc or f"Imported incident record at {loc}",
                            status='approved',
                            reported_by=request.user
                        )
                        imported_count += 1
                    except Exception:
                        error_count += 1

                messages.success(request, f"Successfully imported {imported_count} crime records ({error_count} skipped errors).")
                return redirect('crime_list')
            except Exception as e:
                messages.error(request, f"Failed to parse CSV file: {e}")
    else:
        form = CSVUploadForm()

    return render(request, 'crimes/csv_upload.html', {'form': form})


# =========================
# PUBLIC SAFETY ALERTS
# =========================
@login_required
def alerts_view(request):
    alerts = CrimeAlert.objects.all().order_by('-created_at')
    
    if request.method == 'POST' and request.user.is_staff:
        form = CrimeAlertForm(request.POST)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.created_by = request.user
            alert.save()
            messages.success(request, "Public safety advisory broadcasted successfully.")
            return redirect('alerts_view')
    else:
        form = CrimeAlertForm() if request.user.is_staff else None

    context = {
        'alerts': alerts,
        'form': form,
    }
    return render(request, 'crimes/alerts.html', context)


# =========================
# ADMIN & POLICE COMMAND PORTAL
# =========================
@login_required
@user_passes_test(is_admin_or_staff)
def admin_panel(request):
    users = User.objects.all().order_by('-date_joined')
    all_crimes = CrimeRecord.objects.all().order_by('-created_at')
    
    pending_complaints = all_crimes.filter(status='pending')
    investigating_complaints = all_crimes.filter(status='investigating')
    approved_complaints = all_crimes.filter(status='approved')

    if request.method == 'POST' and 'create_alert' in request.POST:
        alert_form = CrimeAlertForm(request.POST)
        if alert_form.is_valid():
            alert = alert_form.save(commit=False)
            alert.created_by = request.user
            alert.save()
            messages.success(request, "Emergency alert broadcasted to citizen portal.")
            return redirect('admin_panel')
    else:
        alert_form = CrimeAlertForm()

    context = {
        'users': users,
        'pending_complaints': pending_complaints,
        'investigating_complaints': investigating_complaints,
        'approved_complaints': approved_complaints,
        'alert_form': alert_form,
        
        # Stat cards
        'total_users': users.count(),
        'active_users': users.filter(is_active=True).count(),
        'staff_users': users.filter(is_staff=True).count(),
        'total_complaints': all_crimes.count(),
        'pending_count': pending_complaints.count(),
        'investigating_count': investigating_complaints.count(),
        'approved_count': approved_complaints.count(),
        'resolved_count': all_crimes.filter(status='resolved').count(),
        'rejected_count': all_crimes.filter(status='rejected').count(),
    }
    return render(request, 'crimes/admin_panel.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def admin_update_status(request, pk, new_status=None):
    crime = get_object_or_404(CrimeRecord, pk=pk)
    target_status = request.POST.get('new_status') or new_status
    if target_status in ['approved', 'investigating', 'resolved', 'rejected']:
        crime.status = target_status
        crime.save()
        messages.success(request, f"FIR #{crime.fir_number} status updated to {crime.get_status_display()}.")
    return redirect('admin_panel')


@login_required
@user_passes_test(is_admin_or_staff)
def admin_retrain_ml(request):
    result = train_nlp_models()
    messages.success(request, f"ML Prediction Models re-trained successfully with {result['samples_trained']} incident samples!")
    return redirect('ai_analytics')


# =========================
# JSON API FOR LIVE MAP MARKERS
# =========================
@login_required
def crime_api(request):
    crimes = CrimeRecord.objects.filter(status__in=['approved', 'investigating', 'resolved'])
    data = [serialize_record(c) for c in crimes]
    return JsonResponse(data, safe=False)