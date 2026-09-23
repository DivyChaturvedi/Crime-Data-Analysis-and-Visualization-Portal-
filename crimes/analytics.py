"""
CDAVP Data Analytics & Chart Aggregation Module
===============================================
Computes statistical indicators, time-series trends, and formatted datasets
for responsive Chart.js visualizations.
"""

from collections import Counter
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, TruncDate, TruncHour, Coalesce


def get_dashboard_analytics(records):
    """
    Computes comprehensive analytics across approved & active crime records.
    Returns structured data optimized for Chart.js rendering.
    """
    total_count = records.count()
    if total_count == 0:
        return _empty_analytics()

    # 1. CRIME TYPE DISTRIBUTION
    type_counts = records.values('crime_type').annotate(count=Count('id')).order_by('-count')
    type_labels = []
    type_data = []
    
    type_display_map = {
        'theft': 'Theft',
        'assault': 'Assault',
        'robbery': 'Robbery',
        'murder': 'Murder',
        'fraud': 'Fraud & Cybercrime',
        'vandalism': 'Vandalism',
        'drug_offense': 'Drug Offense',
        'burglary': 'Burglary',
        'harassment': 'Harassment',
        'vehicle_theft': 'Vehicle Theft',
        'other': 'Other'
    }

    type_color_map = {
        'theft': '#ef4444',
        'assault': '#f97316',
        'robbery': '#881337',
        'murder': '#450a0a',
        'fraud': '#3b82f6',
        'vandalism': '#64748b',
        'drug_offense': '#10b981',
        'burglary': '#8b5cf6',
        'harassment': '#ec4899',
        'vehicle_theft': '#06b6d4',
        'other': '#6b7280'
    }

    type_colors = []
    for item in type_counts:
        t_key = item['crime_type']
        type_labels.append(type_display_map.get(t_key, t_key.replace('_', ' ').title()))
        type_data.append(item['count'])
        type_colors.append(type_color_map.get(t_key, '#2563eb'))

    # 2. MONTHLY TIMELINE & MOVING AVERAGE
    monthly_raw = (
        records
        .annotate(effective_dt=Coalesce('incident_datetime', 'date_time'))
        .annotate(month=TruncMonth('effective_dt'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    monthly_labels = []
    monthly_values = []
    for m in monthly_raw:
        if m['month']:
            monthly_labels.append(m['month'].strftime('%b %Y'))
            monthly_values.append(m['count'])

    # Fallback if no monthly date could be parsed
    if not monthly_labels:
        monthly_labels = [timezone.now().strftime('%b %Y')]
        monthly_values = [total_count]

    # 3-Month moving average
    moving_avg = []
    window = 3
    for i in range(len(monthly_values)):
        sub = monthly_values[max(0, i - window + 1): i + 1]
        moving_avg.append(round(sum(sub) / len(sub), 1))

    # 3. SEVERITY BREAKDOWN
    sev_counts = Counter(records.values_list('severity_level', flat=True))
    severity_stats = {
        'critical': sev_counts.get('critical', 0),
        'high': sev_counts.get('high', 0),
        'medium': sev_counts.get('medium', 0),
        'low': sev_counts.get('low', 0),
    }

    # 4. 24-HOUR HOURLY RISK CURVE
    hourly_counts = [0] * 24
    for r in records:
        dt = r.incident_datetime or r.date_time
        if dt:
            hourly_counts[dt.hour] += 1
    
    hourly_labels = [f"{h:02d}:00" for h in range(24)]

    # 5. DAY OF WEEK RADAR DISTRIBUTION (0=Mon, 6=Sun)
    day_counts = [0] * 7
    day_labels = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for r in records:
        dt = r.incident_datetime or r.date_time
        if dt:
            day_counts[dt.weekday()] += 1

    # 6. CASE RESOLUTION EFFICIENCY
    all_records = records.model.objects.all()
    all_count = all_records.count()
    resolved_count = all_records.filter(status='resolved').count()
    investigating_count = all_records.filter(status='investigating').count()
    verified_count = all_records.filter(status='approved').count()
    pending_count = all_records.filter(status='pending').count()
    rejected_count = all_records.filter(status='rejected').count()

    resolution_rate = round((resolved_count / all_count * 100), 1) if all_count > 0 else 0.0

    return {
        'total_crimes': total_count,
        'all_records_count': all_count,
        'resolved_count': resolved_count,
        'investigating_count': investigating_count,
        'verified_count': verified_count,
        'pending_count': pending_count,
        'rejected_count': rejected_count,
        'resolution_rate': resolution_rate,
        'clearance_rate': resolution_rate,
        
        # Chart Datasets
        'type_labels': type_labels,
        'type_data': type_data,
        'type_colors': type_colors,
        
        'monthly_labels': monthly_labels,
        'monthly_values': monthly_values,
        'monthly_moving_avg': moving_avg,
        
        'severity_stats': severity_stats,
        
        'hourly_labels': hourly_labels,
        'hourly_data': hourly_counts,
        
        'day_labels': day_labels,
        'day_data': day_counts,
    }


def _empty_analytics():
    return {
        'total_crimes': 0,
        'all_records_count': 0,
        'resolved_count': 0,
        'investigating_count': 0,
        'verified_count': 0,
        'pending_count': 0,
        'rejected_count': 0,
        'resolution_rate': 0.0,
        'clearance_rate': 0.0,
        'type_labels': ['Theft', 'Assault', 'Robbery', 'Other'],
        'type_data': [0, 0, 0, 0],
        'type_colors': ['#ef4444', '#f97316', '#881337', '#6b7280'],
        'monthly_labels': [timezone.now().strftime('%b %Y')],
        'monthly_values': [0],
        'monthly_moving_avg': [0],
        'severity_stats': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0},
        'hourly_labels': [f"{h:02d}:00" for h in range(24)],
        'hourly_data': [0] * 24,
        'day_labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'day_data': [0] * 7,
    }
