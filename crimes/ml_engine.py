"""
CDAVP Machine Learning & Predictive Crime Intelligence Engine
=============================================================
Provides:
1. NLP-based Incident Description Classifier (Crime Category & Severity Prediction).
2. Spatial Hotspot Clustering (DBSCAN & K-Means for geographic high-density zone identification).
3. Temporal-Spatial Risk Probability Scoring Engine.
4. Auto-training & evaluation with fallback synthesis.
"""

import math
import numpy as np
import pandas as pd
from collections import Counter
from datetime import datetime
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import DBSCAN, KMeans
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Fallback training corpus for NLP text classification cold-start
NLP_BOOTSTRAP_DATA = [
    # Theft / Snatching / Pickpocketing
    ("mobile phone snatched while walking on road", "theft", "medium"),
    ("wallet and purse stolen from bag in crowded market", "theft", "low"),
    ("bicycle stolen from outside residential house", "theft", "low"),
    ("shoplifting incident at retail electronics store", "theft", "low"),
    ("laptop snatched by two bike riders at bus stop", "theft", "medium"),
    ("chain snatching near temple in broad daylight", "theft", "high"),
    ("cash stolen from temple donation box", "theft", "low"),
    ("goods stolen from parked delivery truck", "theft", "low"),

    # Vehicle Theft
    ("motorcycle stolen from parking area near railway station", "vehicle_theft", "medium"),
    ("car stolen overnight from outside apartment complex", "vehicle_theft", "medium"),
    ("scooter missing from market parking slot", "vehicle_theft", "medium"),
    ("truck hijacked or stolen from highway dhaba", "vehicle_theft", "high"),

    # Assault / Physical Violence
    ("physical altercation and fist fight outside tea shop", "assault", "medium"),
    ("group attacked a shopkeeper with sticks causing injury", "assault", "high"),
    ("serious injury caused in street fight between two gangs", "assault", "high"),
    ("person beaten up with iron rod in marketplace dispute", "assault", "high"),
    ("neighbor dispute turned violent resulting in bleeding", "assault", "medium"),
    ("unprovoked physical assault on pedestrian at night", "assault", "high"),

    # Robbery / Armed Hold-up
    ("armed robbery at jewelry shop with gun pointed", "robbery", "critical"),
    ("knife held to throat while taking cash and gold ornaments", "robbery", "critical"),
    ("cash delivery van intercepted by armed masked men", "robbery", "critical"),
    ("petrol pump looted at midnight by armed criminals", "robbery", "critical"),
    ("highway robbery targeting night travelers with weapons", "robbery", "critical"),

    # Burglary & Break-in
    ("house lock broken while family was out of station", "burglary", "medium"),
    ("shop shutter forced open overnight and cash box emptied", "burglary", "medium"),
    ("apartment door lock picked and electronic items stolen", "burglary", "medium"),
    ("warehouse broken into and valuable inventory stolen", "burglary", "high"),

    # Fraud & Cybercrime
    ("bank account emptied through phishing OTP fraud call", "fraud", "medium"),
    ("fake loan app extorting money and blackmailing victim", "fraud", "high"),
    ("counterfeit fake currency notes circulated in market", "fraud", "medium"),
    ("credit card cloned and unauthorized online transactions made", "fraud", "medium"),
    ("investment scam promised double returns and took money", "fraud", "high"),
    ("social media account hacked and money demanded from contacts", "fraud", "medium"),

    # Drug Offense / Narcotics
    ("illegal drug peddling reported near college campus", "drug_offense", "high"),
    ("contraband narcotics packet seized from suspect vehicle", "drug_offense", "high"),
    ("smuggling of illicit substances across state borders", "drug_offense", "high"),
    ("illicit liquor brewery and distribution found in rural area", "drug_offense", "medium"),

    # Vandalism & Property Damage
    ("public bus stop glass shattered and walls defaced", "vandalism", "low"),
    ("cars parked in street keyed and tires punctured deliberately", "vandalism", "low"),
    ("street lights and government property damaged during protest", "vandalism", "medium"),
    ("shop windows broken with stones during late night hours", "vandalism", "low"),

    # Harassment & Stalking
    ("woman harassed and followed continuously on street", "harassment", "high"),
    ("lewd comments and stalking reported outside girls school", "harassment", "high"),
    ("online harassment and threatening messages sent repeatedly", "harassment", "medium"),
    ("workplace intimidation and persistent stalking", "harassment", "medium"),

    # Murder / Fatal Incident
    ("dead body found with severe wounds near railway tracks", "murder", "critical"),
    ("fatal shooting incident during gang rivalry", "murder", "critical"),
    ("homicide case reported inside locked residential premises", "murder", "critical"),
    ("fatal stabbing outside bar following heated argument", "murder", "critical"),
]

# Global cached ML model pipelines
_nlp_category_model = None
_nlp_severity_model = None
_model_last_trained = None


def train_nlp_models():
    """Trains the NLP classification pipelines using DB records + bootstrap dataset."""
    global _nlp_category_model, _nlp_severity_model, _model_last_trained
    from crimes.models import CrimeRecord

    texts = [item[0] for item in NLP_BOOTSTRAP_DATA]
    categories = [item[1] for item in NLP_BOOTSTRAP_DATA]
    severities = [item[2] for item in NLP_BOOTSTRAP_DATA]

    # Augment with existing database descriptions
    try:
        db_records = CrimeRecord.objects.exclude(description__exact='').filter(status__in=['approved', 'investigating', 'resolved'])
        for rec in db_records:
            if len(rec.description.strip()) > 10:
                texts.append(rec.description.strip())
                categories.append(rec.crime_type)
                severities.append(rec.severity_level)
    except Exception:
        pass

    # Pipeline for Crime Type Prediction
    cat_pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), stop_words='english', min_df=1)),
        ('clf', MultinomialNB(alpha=0.3))
    ])
    cat_pipeline.fit(texts, categories)
    _nlp_category_model = cat_pipeline

    # Pipeline for Severity Prediction
    sev_pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), stop_words='english', min_df=1)),
        ('clf', RandomForestClassifier(n_estimators=50, random_state=42))
    ])
    sev_pipeline.fit(texts, severities)
    _nlp_severity_model = sev_pipeline

    _model_last_trained = timezone.now()
    return {
        'status': 'success',
        'samples_trained': len(texts),
        'timestamp': _model_last_trained.isoformat()
    }


def predict_incident_features(description_text):
    """
    Given a crime description, predicts the most probable crime type, severity,
    and associated confidence level.
    """
    global _nlp_category_model, _nlp_severity_model
    if _nlp_category_model is None or _nlp_severity_model is None:
        train_nlp_models()

    cleaned = description_text.strip().lower() if description_text else ""
    if not cleaned or len(cleaned) < 4:
        return {
            'predicted_crime_type': 'other',
            'crime_type_display': 'Other Incident',
            'predicted_severity': 'medium',
            'severity_display': 'Medium Risk',
            'confidence': 0.5,
            'top_probabilities': []
        }

    # Predict crime type & probability
    probs = _nlp_category_model.predict_proba([cleaned])[0]
    classes = _nlp_category_model.classes_
    top_indices = np.argsort(probs)[::-1]

    pred_cat = classes[top_indices[0]]
    confidence = float(probs[top_indices[0]])

    top_candidates = [
        {'type': classes[idx], 'confidence': round(float(probs[idx]) * 100, 1)}
        for idx in top_indices[:3]
    ]

    # Predict severity
    pred_sev = _nlp_severity_model.predict([cleaned])[0]

    # Human-readable displays
    cat_displays = {
        'theft': 'Theft',
        'assault': 'Assault',
        'robbery': 'Robbery',
        'murder': 'Murder',
        'fraud': 'Fraud & Cybercrime',
        'vandalism': 'Vandalism',
        'drug_offense': 'Drug Offense',
        'burglary': 'Burglary & Break-in',
        'harassment': 'Harassment & Stalking',
        'vehicle_theft': 'Vehicle Theft',
        'other': 'Other Incident'
    }

    return {
        'predicted_crime_type': pred_cat,
        'crime_type_display': cat_displays.get(pred_cat, pred_cat.replace('_', ' ').title()),
        'predicted_severity': pred_sev,
        'severity_display': pred_sev.capitalize() + ' Risk',
        'confidence': round(confidence, 3),
        'top_candidates': top_candidates
    }


def compute_spatial_clusters(records, eps_km=1.2, min_samples=2):
    """
    Applies DBSCAN density clustering & K-Means to identify spatial crime hotspots.
    Returns structured cluster summaries with centroid, radius, risk tier, and counts.
    """
    valid_pts = []
    record_list = list(records)

    for r in record_list:
        if r.latitude is not None and r.longitude is not None:
            if -90 <= r.latitude <= 90 and -180 <= r.longitude <= 180:
                valid_pts.append({
                    'id': r.id,
                    'lat': r.latitude,
                    'lng': r.longitude,
                    'type': r.crime_type,
                    'type_display': r.get_crime_type_display(),
                    'severity': r.severity_level,
                    'location': r.location_name,
                    'datetime': r.incident_datetime or r.date_time
                })

    if len(valid_pts) < 2:
        return []

    # Coordinates in radians for haversine / spatial metric
    coords = np.array([[p['lat'], p['lng']] for p in valid_pts])

    # Convert eps_km to radians on Earth (radius ≈ 6371 km)
    kms_per_radian = 6371.0088
    epsilon = eps_km / kms_per_radian

    # Run DBSCAN
    coords_rad = np.radians(coords)
    db = DBSCAN(eps=epsilon, min_samples=min_samples, metric='haversine').fit(coords_rad)
    labels = db.labels_

    clusters = {}
    for idx, label in enumerate(labels):
        if label == -1:
            # Noise point
            cluster_id = f"isolated_{idx}"
        else:
            cluster_id = f"cluster_{label}"

        if cluster_id not in clusters:
            clusters[cluster_id] = {
                'id': cluster_id,
                'is_noise': (label == -1),
                'points': [],
                'types': Counter(),
                'severities': Counter(),
                'locations': Counter(),
            }

        pt = valid_pts[idx]
        clusters[cluster_id]['points'].append(pt)
        clusters[cluster_id]['types'][pt['type_display']] += 1
        clusters[cluster_id]['severities'][pt['severity']] += 1
        if pt['location']:
            clusters[cluster_id]['locations'][pt['location']] += 1

    results = []
    for c_id, data in clusters.items():
        pts = data['points']
        count = len(pts)
        if count == 0:
            continue

        lats = [p['lat'] for p in pts]
        lngs = [p['lng'] for p in pts]
        center_lat = round(float(np.mean(lats)), 6)
        center_lng = round(float(np.mean(lngs)), 6)

        # Calculate max radius in meters from centroid
        max_dist_m = 100.0
        for p in pts:
            d_lat = math.radians(p['lat'] - center_lat)
            d_lng = math.radians(p['lng'] - center_lng)
            a = math.sin(d_lat / 2)**2 + math.cos(math.radians(center_lat)) * math.cos(math.radians(p['lat'])) * math.sin(d_lng / 2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            dist_m = 6371000 * c
            if dist_m > max_dist_m:
                max_dist_m = dist_m

        radius_m = min(round(max_dist_m + 80, 1), 1500.0)

        # Determine dominant features
        top_type = data['types'].most_common(1)[0][0] if data['types'] else 'General'
        top_location = data['locations'].most_common(1)[0][0] if data['locations'] else 'Zone'

        # Risk level determination based on density and critical severities
        sev_counts = data['severities']
        critical_score = (sev_counts.get('critical', 0) * 3) + (sev_counts.get('high', 0) * 2) + count

        if critical_score >= 6 or count >= 5:
            alert_level = 'red'
            risk_label = 'High Danger Zone'
        elif critical_score >= 3 or count >= 2:
            alert_level = 'yellow'
            risk_label = 'Moderate Caution Zone'
        else:
            alert_level = 'green'
            risk_label = 'Low Risk Normal Area'

        results.append({
            'cluster_id': c_id,
            'location_name': top_location,
            'latitude': center_lat,
            'longitude': center_lng,
            'radius_meters': radius_m,
            'report_count': count,
            'alert_level': alert_level,
            'risk_label': risk_label,
            'top_crime': top_type,
            'critical_count': sev_counts.get('critical', 0),
            'high_count': sev_counts.get('high', 0),
            'medium_count': sev_counts.get('medium', 0),
            'low_count': sev_counts.get('low', 0),
        })

    # Sort descending by report count
    results.sort(key=lambda x: -x['report_count'])
    return results


def calculate_risk_probability(latitude, longitude, target_datetime=None, records=None):
    """
    Calculates a predictive Risk Probability Score (0 - 100%) for a coordinate point and time.
    Combines spatial proximity, historical incident density, hourly risk curve, and day-of-week factors.
    """
    from crimes.models import CrimeRecord

    if target_datetime is None:
        target_datetime = timezone.now()

    if records is None:
        records = CrimeRecord.objects.filter(status__in=['approved', 'investigating', 'resolved'])

    target_hour = target_datetime.hour
    target_weekday = target_datetime.weekday()  # 0=Monday, 6=Sunday

    # Hourly baseline risk multiplier (late night/early morning has higher risk)
    # Peak risk usually 20:00 - 04:00
    if 0 <= target_hour < 4:
        hour_multiplier = 1.35
    elif 4 <= target_hour < 8:
        hour_multiplier = 0.85
    elif 8 <= target_hour < 12:
        hour_multiplier = 0.90
    elif 12 <= target_hour < 16:
        hour_multiplier = 1.05
    elif 16 <= target_hour < 20:
        hour_multiplier = 1.20
    else:  # 20 to 24
        hour_multiplier = 1.40

    # Weekend factor (Friday, Saturday, Sunday nights often have higher activity)
    weekday_multiplier = 1.15 if target_weekday in [4, 5, 6] else 0.95

    # Spatial distance scoring
    total_weighted_proximity = 0.0
    nearby_crimes_count = 0
    nearest_dist_km = 999.0
    dominant_crime_counter = Counter()

    for r in records:
        if r.latitude is None or r.longitude is None:
            continue

        d_lat = math.radians(r.latitude - latitude)
        d_lng = math.radians(r.longitude - longitude)
        a = math.sin(d_lat / 2)**2 + math.cos(math.radians(latitude)) * math.cos(math.radians(r.latitude)) * math.sin(d_lng / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist_km = 6371.0 * c

        if dist_km < nearest_dist_km:
            nearest_dist_km = dist_km

        # Within 3 km radius affects the score
        if dist_km <= 3.0:
            nearby_crimes_count += 1
            dominant_crime_counter[r.get_crime_type_display()] += 1

            # Severity weights
            sev_wt = {
                'critical': 2.5,
                'high': 1.8,
                'medium': 1.2,
                'low': 0.8
            }.get(r.severity_level, 1.0)

            # Inverse distance weighting
            proximity_score = (1.0 / (dist_km + 0.2)) * sev_wt
            total_weighted_proximity += proximity_score

    # Compute baseline risk (0 to 100)
    raw_score = (total_weighted_proximity * 7.5) * hour_multiplier * weekday_multiplier
    # Normalize between 5% (safe baseline) and 96%
    risk_score = round(float(np.clip(raw_score, 8.0, 96.0)), 1)

    if risk_score >= 65.0:
        risk_level = 'high'
        risk_label = 'High Risk Alert'
        badge_class = 'danger'
        recommendations = [
            "Heavy police patrol frequency advised during night shifts.",
            "Install high-definition CCTV surveillance and well-lit street fixtures.",
            "Citizens should avoid walking alone after 9 PM in isolated lanes.",
            "Emergency PCR van on standby within 5 minutes radius."
        ]
    elif risk_score >= 35.0:
        risk_level = 'medium'
        risk_label = 'Moderate Caution Zone'
        badge_class = 'warning'
        recommendations = [
            "Regular periodic patrol checks scheduled during evening hours.",
            "Verify shop security systems and neighborhood watch communication.",
            "Keep emergency contact numbers saved on speed dial."
        ]
    else:
        risk_level = 'low'
        risk_label = 'Low Risk Safe Area'
        badge_class = 'success'
        recommendations = [
            "Normal routine surveillance is sufficient.",
            "Standard community safety precautions apply."
        ]

    top_crime = dominant_crime_counter.most_common(1)[0][0] if dominant_crime_counter else 'Theft'

    return {
        'risk_score': risk_score,
        'risk_level': risk_level,
        'risk_label': risk_label,
        'badge_class': badge_class,
        'nearby_incidents_3km': nearby_crimes_count,
        'nearest_incident_distance_km': round(nearest_dist_km, 2) if nearest_dist_km < 990 else None,
        'predicted_primary_threat': top_crime,
        'recommendations': recommendations,
        'hour_multiplier': hour_multiplier,
        'time_evaluated': target_datetime.strftime('%d %b %Y, %I:%M %p')
    }
