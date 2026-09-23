# 🛡️ Crime Data Analysis & Visualization Portal (CDAVP)

[![Django](https://img.shields.io/badge/Django-5.0+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=Leaflet&logoColor=white)](https://leafletjs.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

> **An AI-powered Crime Intelligence, Predictive Analytics, Geo-Spatial Hotspot Mapping & Public Safety Management System.**

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture & ML Engine](#-system-architecture--ml-engine)
- [Security & Hardening Architecture](#-security--hardening-architecture)
- [Tech Stack](#-tech-stack)
- [Project Directory Structure](#-project-directory-structure)
- [Getting Started / Installation](#-getting-started--installation)
- [Default Demo Credentials](#-default-demo-credentials)
- [Platform Navigation & Routes](#-platform-navigation--routes)
- [REST API Reference](#-rest-api-reference)
- [Bulk Data Import Format](#-bulk-data-import-format)
- [Future Roadmap](#-future-roadmap)
- [License & Author](#-license--author)

---

## 📖 Overview

**Crime Data Analysis and Visualization Portal (CDAVP)** is a comprehensive full-stack web platform built for law enforcement agencies, civic administrations, and citizens. It streamlines the entire crime reporting lifecycle: from online citizen complaint / FIR registration to automated text classification, spatial hotspot detection, predictive risk modeling, and instant PDF docket generation.

Designed around real-world municipal and district policing scenarios (configured with geo-spatial boundaries for **Khargone District, MP**), CDAVP equips officers with high-velocity investigative tools while giving citizens a transparent, secure window into public safety.

---

## ⚡ Key Features

### 📊 1. Real-Time Investigative Dashboard
- **Executive KPI Cards**: Real-time stats on total FIRs, active investigations, solved cases, and critical risk threats.
- **Dynamic Data Visualizations**: Built with Chart.js — crime category distribution, monthly incident velocity trends, severity breakdowns, and hourly crime peak distributions.
- **Multi-Dimensional Filters**: Filter records by date range, crime category, police jurisdiction, and severity levels.

### 🧠 2. AI & Predictive Crime Intelligence Engine
- **NLP Incident Text Classifier**: Uses TF-IDF vectorization with Multinomial Naive Bayes & Random Forest classifiers to predict crime category and risk level directly from complaint narratives.
- **Spatial Hotspot Clustering**: Applies **DBSCAN** and **K-Means** spatial clustering to pinpoint geographical high-density crime clusters.
- **Dynamic Risk Probability Scoring**: Calculates a 0–100% situational danger score and confidence metric based on historical temporal-spatial patterns.
- **On-Demand Model Retraining**: Police admins can trigger automated model retraining as fresh FIR records are logged.

### 🗺️ 3. Interactive GIS Hotspot Mapping
- **Geographic Visualization**: Powered by Leaflet.js with OpenStreetMap tiles.
- **Boundary Precision**: Integrated with Khargone district GeoJSON boundary polygon verification (using Shapely geometry).
- **Smart Visuals**: Severity-coded markers (Critical, High, Medium, Low), incident popups with full FIR metadata, and dynamic marker clustering.

### 📋 4. End-to-End FIR & Complaint Management
- **Citizen E-Filing**: Intuitive complaint submission with location coordinates, nearest landmark, date-time pickers, weapon tracking, and victim demographic metadata.
- **Evidence Attachment**: Secure multi-format upload with strict file type and size restrictions.
- **Automated Case Tracking**: Auto-generates unique FIR case numbers (e.g. `FIR-202609-A4F19B`).
- **Complete Workflow Lifecycle**: Status transitions from `Pending Verification` ➔ `Approved & Registered` ➔ `Under Active Investigation` ➔ `Case Solved / Closed` or `Rejected`.

### 📄 5. Automated PDF Docket & Report Generation
- **Official FIR PDF Export**: One-click generation of court-admissible, formatted FIR PDF dockets using ReportLab.
- **District Crime Bulletin**: Download aggregated police briefing reports and statistics in PDF.
- **Bulk Data Handling**: Upload CSV files for mass historical imports and export filtered datasets with a single click.

### 🚨 6. Public Safety & Emergency Broadcasting
- **24/7 Helpline SOS Ribbon**: Immediate top-bar access to National Emergency (112 / 100), Women Helpline (1090), Cyber Crime Helpline (1930), and Ambulance (108).
- **Public Safety Broadcasts**: Real-time bulletins for high-risk advisories, night patrol dispatch notices, and emergency alerts.

### 🚔 7. Police Command Center & Patrol Dispatcher
- **Staff-Only Admin Panel**: Centralized incident review, quick CSRF-protected status updates, and Investigating Officer (IO) assignments.
- **Patrol Scheduling System**: Shift-based patrol scheduling (Morning, Evening, Night) with assigned PCR units, sectors, and officer-in-charge contacts.

### 🔐 8. Authentication & Role-Based Access Control (RBAC)
- Multi-tier permission levels: **Super Administrator**, **Police Officer / Staff**, and **Citizen User**.
- Two-Factor / OTP verification flow for new citizen registrations with brute-force lockout.
- Citizen profile dashboard to track all personal lodged complaints in real time.

---

## 🛠️ System Architecture & ML Engine

```text
       ┌────────────────────────────────────────────────────────┐
       │                  CDAVP Web Interface                   │
       │   (Bootstrap 5.3 + FontAwesome + Leaflet.js + Chart.js) │
       └───────────────────────────┬────────────────────────────┘
                                   │ HTTP / AJAX
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │                   Django 5.0 Core                      │
       │   ┌─────────────────────┐   ┌──────────────────────┐   │
       │   │   Accounts App      │   │     Crimes App       │   │
       │   │  (Auth, RBAC, OTP)  │   │ (CRUD, FIR, Alerts)  │   │
       │   └─────────────────────┘   └──────────┬───────────┘   │
       └────────────────────────────────────────┼───────────────┘
                                                │
                 ┌──────────────────────────────┼──────────────────────────────┐
                 ▼                              ▼                              ▼
      ┌─────────────────────┐        ┌─────────────────────┐        ┌─────────────────────┐
      │   ML & AI Engine    │        │  Spatial & Mapping  │        │ Reporting & Exports │
      │  - TF-IDF + MNB/RF  │        │ - Leaflet.js Tiles  │        │ - ReportLab FIR PDF │
      │  - DBSCAN Hotspots  │        │ - Shapely Polygons  │        │ - Crime Bulletin    │
      │  - Risk Probability │        │ - Khargone GeoJSON  │        │ - CSV Data Pipelines│
      └─────────────────────┘        └─────────────────────┘        └─────────────────────┘
                 │                              │                              │
                 └──────────────────────────────┼──────────────────────────────┘
                                                ▼
                                    ┌───────────────────────┐
                                    │  Database (SQLite /   │
                                    │     PostgreSQL)       │
                                    └───────────────────────┘
```

---

## 🔒 Security & Hardening Architecture

CDAVP is designed following OWASP Top 10 guidelines and secure engineering practices:

- **SQL Injection Immunity**: 100% of database interactions utilize Django's ORM parameterized queries with zero raw SQL execution.
- **CSRF Defense**: All state-changing forms and administrative status changes enforce POST-only requests with CSRF token verification.
- **File Upload Hardening**: Evidence attachments are restricted to approved formats (`.pdf`, `.jpg`, `.jpeg`, `.png`, `.webp`) with a strict 5 MB size limit.
- **CSPRNG OTP Generator**: OTP verification employs Python's `secrets` / `random.SystemRandom()` for cryptographically secure pseudo-random numbers with automatic account lockout after 5 failed attempts.
- **Formula Injection Defense (CWE-1236)**: Exported CSV fields are automatically sanitized against spreadsheet formula injection triggers (`=`, `+`, `-`, `@`).
- **Production Safety Guards**: The database seeder (`seed_data`) contains an active runtime guard that blocks execution when `DEBUG=False` unless the explicit `--force` flag is supplied.

---

## 💻 Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Django 5.0 (Python 3.10+) |
| **Machine Learning & Data** | Scikit-learn, Pandas, NumPy, Shapely |
| **GIS & Mapping** | Leaflet.js 1.9, OpenStreetMap, GeoJSON |
| **Data Visualization** | Chart.js 4.4, Bootstrap 5.3, Font Awesome 6.5 |
| **Reporting & Exporting** | ReportLab (PDF Engine), Python CSV Engine |
| **WSGI / Production Server**| WhiteNoise, Waitress (Windows), Gunicorn (Linux) |
| **Database** | SQLite (Development) / PostgreSQL Ready |

---

## 📂 Project Directory Structure

```text
CDAVP/
├── accounts/                   # Authentication & user management app
│   ├── migrations/             # Database migration files
│   ├── templates/accounts/     # Login, Register, OTP verification, Profile
│   ├── forms.py                # User registration & profile forms
│   ├── models.py               # EmailOTP & UserProfile models
│   ├── urls.py                 # Account routing endpoints
│   └── views.py                # Auth lifecycle & OTP logic
├── cdavp/                      # Django project configuration package
│   ├── asgi.py                 # ASGI entrypoint
│   ├── settings.py             # Global settings (apps, DB, static, auth)
│   ├── urls.py                 # Root URL configuration
│   └── wsgi.py                 # WSGI entrypoint
├── crimes/                     # Core crime intelligence & analytics app
│   ├── management/commands/    # CLI tools (seed_data.py for demo database)
│   ├── migrations/             # CrimeRecord, Alert & Patrol migrations
│   ├── templates/crimes/       # Dashboard, Hotspot Map, AI Analytics, FIR CRUD
│   ├── analytics.py            # Aggregations, time-series, KPI calculations
│   ├── forms.py                # FIR filing, CSV upload & filter forms
│   ├── ml_engine.py            # NLP classification, DBSCAN & risk scoring
│   ├── models.py               # CrimeRecord, CrimeAlert, PatrolSchedule
│   ├── reports.py              # ReportLab PDF docket generation
│   ├── urls.py                 # Crime routes & REST API endpoints
│   └── views.py                # Request handlers, views & API endpoints
├── media/                      # Uploaded media (evidence, FIR proof files)
├── static/                     # Static assets
│   ├── css/style.css           # Custom theme stylesheet
│   ├── js/app.js               # Interactive frontend scripting
│   └── maps/khargone.geojson   # District boundary GeoJSON polygon
├── templates/                  # Base layouts & HTTP error templates
│   ├── base.html               # Main navbar, SOS ribbon & footer
│   ├── 404.html                # Not Found page
│   └── 500.html                # Internal Server Error page
├── .env.example                # Sample environment configuration
├── .gitignore                  # Git ignore rules
├── LICENSE                     # MIT Open Source License
├── manage.py                   # Django CLI management utility
├── requirements.txt            # Python dependencies
├── run_server.bat              # One-click Windows launch script
└── sample_data.csv             # Sample dataset for bulk upload
```

---

## 🚀 Getting Started / Installation

Follow these steps to set up and run the portal locally on your machine.

### 1. Prerequisites
Ensure you have the following installed:
- **Python 3.10** or higher ([Download Python](https://www.python.org/downloads/))
- **Git** ([Download Git](https://git-scm.com/downloads))

---

### 2. Clone the Repository

```bash
git clone https://github.com/DivyChaturvedi/Crime-Data-Analysis-and-Visualization-Portal-.git
cd Crime-Data-Analysis-and-Visualization-Portal-
```

*(If running from local source folder, navigate to the directory where `manage.py` is located).*

---

### 3. Create & Activate Virtual Environment

**On Windows (PowerShell / Command Prompt):**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 4. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 5. Setup Environment Variables

Copy the `.env.example` file to create your local `.env`:

```bash
# On Windows
copy .env.example .env

# On macOS/Linux
cp .env.example .env
```

---

### 6. Apply Database Migrations

```bash
python manage.py migrate
```

---

### 7. Seed Initial Demo Data *(Recommended for Local Testing)*

Populate your database with realistic Khargone district crime records, patrol schedules, public safety alerts, and pre-configured accounts:

```bash
python manage.py seed_data
```

---

### 8. Run Development Server

```bash
python manage.py runserver
```

Or on Windows, simply double-click:
```bash
run_server.bat
```

Now open your browser and navigate to:
👉 **`http://127.0.0.1:8000/`**

---

## 🔑 Default Demo Credentials

> [!IMPORTANT]
> **Security Notice:** The accounts below are created strictly for local sandbox testing and academic review. In production deployments, never use default credentials; always create a dedicated superuser using `python manage.py createsuperuser` with a strong, private password.

| Role | Username | Password | Access Level |
|---|---|---|---|
| **Super Administrator** | `admin` | `Admin@2026` | Full Control (Django Admin, Command Panel, ML Retrain) |
| **Police Officer** | `officer1` | `Officer@2026` | Staff Access (Case Investigations, Admin Panel, Patrols) |
| **Citizen User** | `citizen1` | `Citizen@2026` | Citizen Access (File FIR, Track Complaints, Profile) |

---

## 🧭 Platform Navigation & Routes

| URL Route | Purpose | Access |
|---|---|---|
| `/` or `/dashboard/` | Real-time investigative dashboard & charts | Public / All |
| `/ai-analytics/` | AI predictive risk score & NLP classifier | Public / All |
| `/map/` | Interactive GIS crime hotspot map | Public / All |
| `/crimes/` | Complete FIR complaint register | Public / All |
| `/crimes/add/` | File new FIR with evidence upload | Registered Users |
| `/crimes/<id>/` | Detailed incident dossier & timeline | Registered Users |
| `/crimes/<id>/pdf/` | Download official FIR copy in PDF format | Registered Users |
| `/alerts/` | Public safety broadcasts & emergency advisories | Public / All |
| `/admin-panel/` | Police command center & status management | Staff / Admins |
| `/reports/bulletin/pdf/`| Export district crime bulletin PDF | Staff / Admins |
| `/crimes/upload/` | Bulk CSV complaint import | Staff / Admins |
| `/admin/` | Django standard administration console | Super Admins |

---

## 🔌 REST API Reference

The portal exposes authenticated JSON endpoints for integration with external dashboards, emergency services, or mobile applications:

| Endpoint | Method | Params / Payload | Description |
|---|---|---|---|
| `/api/crimes/` | `GET` | None | Returns verified crime records in JSON format with coordinates and metadata for dynamic map rendering. |
| `/api/ml/predict/` | `GET` | `?lat=21.8247&lng=75.6102` | Calculates real-time spatio-temporal risk score (0-100%) and confidence metric for given coordinates. |
| `/api/ml/classify-text/` | `GET` | `?text=Incident+description...` | Classifies narrative text using TF-IDF NLP model to return predicted crime category and severity level. |

---

## 📑 Bulk Data Import Format

To upload bulk crime records via `/crimes/upload/`, use a CSV file with this structure:

```csv
crime_type,date_time,location_name,latitude,longitude,description
theft,2026-03-15 14:30:00,MG Road Khargone,21.8234,75.6150,Mobile phone snatched by bike riders
robbery,2026-03-16 21:15:00,Gandhi Chowk,21.8240,75.6140,Armed robbery at convenience store
assault,2026-03-17 19:45:00,Naya Bazaar,21.8210,75.6130,Physical altercation outside market
```

*Supported crime types:* `theft`, `assault`, `robbery`, `murder`, `fraud`, `vandalism`, `drug_offense`, `burglary`, `harassment`, `vehicle_theft`, `other`.

---

## 🔮 Future Roadmap

- [ ] Real-time WebSocket alerts via Django Channels for live emergency broadcast popups.
- [ ] Integration with SMS gateways (Twilio / Fast2SMS) for real-time citizen FIR status updates.
- [ ] Deep Learning (LSTM / Transformer) based spatio-temporal crime forecasting.
- [ ] Multilingual support (Hindi and regional language interface toggle).
- [ ] Mobile app client via Flutter / React Native consuming the REST APIs.

---

## 📄 License & Author

- **Author**: [Divy Chaturvedi](https://github.com/DivyChaturvedi)
- **Repository**: [Crime-Data-Analysis-and-Visualization-Portal-](https://github.com/DivyChaturvedi/Crime-Data-Analysis-and-Visualization-Portal-)
- **License**: Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.

---

<p align="center">
  <b>Built with ❤️ for Smarter Law Enforcement & Safer Communities.</b>
</p>
