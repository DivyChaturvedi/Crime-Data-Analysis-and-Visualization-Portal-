"""
CDAVP Automated PDF Reporting Module
====================================
Generates official FIR Acknowledgment Slips and District Crime Intelligence Bulletins
using ReportLab with clean styling and layout.
"""

import io
from datetime import datetime
from django.http import HttpResponse
from django.utils import timezone

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY


def generate_fir_pdf(crime):
    """
    Generates a formal FIR Complaint Acknowledgment Certificate / Slip for a specific crime record.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        alignment=TA_CENTER
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
        alignment=TA_CENTER
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=8,
        spaceAfter=4
    )

    cell_label = ParagraphStyle(
        'CellLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    cell_val = ParagraphStyle(
        'CellVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0f172a')
    )

    elements = []

    # HEADER BLOCK
    elements.append(Paragraph("GOVERNMENT OF MADHYA PRADESH - POLICE DEPARTMENT", subtitle_style))
    elements.append(Paragraph("CRIME DATA ANALYSIS & VISUALIZATION PLATFORM (CDAVP)", title_style))
    elements.append(Paragraph("OFFICIAL FIRST INFORMATION REPORT (FIR) ACKNOWLEDGMENT SLIP", ParagraphStyle('SubSub', parent=subtitle_style, fontName='Helvetica-Bold', textColor=colors.HexColor('#2563eb'))))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceBefore=2, spaceAfter=10))

    # META STRIP
    incident_dt_str = (crime.incident_datetime or crime.date_time).strftime('%d %B %Y at %I:%M %p')
    generated_dt_str = timezone.now().strftime('%d %B %Y, %I:%M %p')
    reporter_name = crime.reported_by.get_full_name() or crime.reported_by.username if crime.reported_by else "Citizen / Anonymous"

    fir_info_data = [
        [
            Paragraph(f"<b>FIR Tracking Number:</b> {crime.fir_number}", cell_val),
            Paragraph(f"<b>Case Status:</b> {crime.get_status_display().upper()}", cell_val)
        ],
        [
            Paragraph(f"<b>Jurisdiction Station:</b> {crime.police_station}", cell_val),
            Paragraph(f"<b>Incident Date & Time:</b> {incident_dt_str}", cell_val)
        ]
    ]

    fir_table = Table(fir_info_data, colWidths=[260, 260])
    fir_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(fir_table)
    elements.append(Spacer(1, 14))

    # SECTION 1: INCIDENT DETAILS
    elements.append(Paragraph("1. INCIDENT & OFFENSE SPECIFICATIONS", section_heading))
    
    details_data = [
        [Paragraph("Offense Category", cell_label), Paragraph(crime.get_crime_type_display(), cell_val)],
        [Paragraph("Severity Level", cell_label), Paragraph(crime.get_severity_level_display(), cell_val)],
        [Paragraph("Incident Location", cell_label), Paragraph(crime.location_name or "Not Specified", cell_val)],
        [Paragraph("Landmark", cell_label), Paragraph(crime.landmark or "N/A", cell_val)],
        [Paragraph("GPS Coordinates", cell_label), Paragraph(f"Lat: {crime.latitude:.6f}, Long: {crime.longitude:.6f}", cell_val)],
        [Paragraph("Weapon / Means", cell_label), Paragraph(crime.weapon_involved or "None", cell_val)],
        [Paragraph("Investigating Officer", cell_label), Paragraph(crime.investigating_officer or "Assigned on Duty", cell_val)],
        [Paragraph("Reported By", cell_label), Paragraph(reporter_name, cell_val)],
    ]

    details_table = Table(details_data, colWidths=[160, 360])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 14))

    # SECTION 2: DESCRIPTION
    elements.append(Paragraph("2. INCIDENT NARRATIVE & COMPLAINT DETAILS", section_heading))
    desc_p = Paragraph(crime.description.replace('\n', '<br/>'), cell_val)
    desc_table = Table([[desc_p]], colWidths=[520])
    desc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ffffff')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(desc_table)
    elements.append(Spacer(1, 14))

    # SECTION 3: OFFICIAL ACTIONS & REMARKS
    if crime.admin_remark:
        elements.append(Paragraph("3. POLICE DEPARTMENT / ADMINISTRATIVE REMARKS", section_heading))
        remark_p = Paragraph(crime.admin_remark.replace('\n', '<br/>'), cell_val)
        remark_table = Table([[remark_p]], colWidths=[520])
        remark_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fefce8')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#fde047')),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(remark_table)
        elements.append(Spacer(1, 14))

    # SIGNATURE BLOCK
    elements.append(Spacer(1, 20))
    sig_data = [
        [
            Paragraph("<b>Digitally Verified By:</b><br/>CDAVP Automated Security Engine<br/>Govt. of Madhya Pradesh", cell_val),
            Paragraph("<b>Station Officer Signature / Seal:</b><br/><br/>_______________________<br/>Officer-in-Charge", ParagraphStyle('SigR', parent=cell_val, alignment=TA_RIGHT))
        ]
    ]
    sig_table = Table(sig_data, colWidths=[260, 260])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 15))

    # FOOTER NOTE
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#94a3b8'), spaceBefore=5, spaceAfter=5))
    elements.append(Paragraph(f"This is a system-generated official FIR acknowledgment slip generated on {generated_dt_str}. Valid for legal tracking.", ParagraphStyle('Foot', parent=subtitle_style, fontSize=8, textColor=colors.HexColor('#64748b'))))

    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{crime.fir_number}.pdf"'
    return response


def generate_bulletin_pdf(records, alert_summary, hotspot_areas):
    """
    Generates a District Crime Intelligence Bulletin PDF summarizing overall statistics,
    hotspots, and security status.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'BullTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        alignment=TA_CENTER
    )

    sub_style = ParagraphStyle(
        'BullSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
        alignment=TA_CENTER
    )

    h2_style = ParagraphStyle(
        'BullH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=10,
        spaceAfter=6
    )

    cell_bold = ParagraphStyle('CBold', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.HexColor('#1e293b'))
    cell_norm = ParagraphStyle('CNorm', fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor('#334155'))

    elements = []

    # Title
    elements.append(Paragraph("CRIME DATA ANALYSIS & VISUALIZATION PLATFORM (CDAVP)", sub_style))
    elements.append(Paragraph("DISTRICT CRIME INTELLIGENCE BULLETIN", title_style))
    elements.append(Paragraph(f"Official Law Enforcement Briefing - Generated {timezone.now().strftime('%d %B %Y, %H:%M')}", sub_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1e3a8a'), spaceBefore=6, spaceAfter=12))

    # EXECUTIVE SUMMARY METRICS
    total_cases = records.count()
    red_count = alert_summary.get('red_count', 0)
    yellow_count = alert_summary.get('yellow_count', 0)
    green_count = alert_summary.get('green_count', 0)

    summary_data = [
        [
            Paragraph(f"<b>Total Registered Crimes:</b> {total_cases}", cell_bold),
            Paragraph(f"<b>Red Alert Hotspots:</b> {red_count}", cell_bold),
            Paragraph(f"<b>Caution Zones (Yellow):</b> {yellow_count}", cell_bold),
            Paragraph(f"<b>Safe Sectors (Green):</b> {green_count}", cell_bold),
        ]
    ]

    summary_table = Table(summary_data, colWidths=[135, 135, 135, 135])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 12))

    # HOTSPOT CLUSTERS TABLE
    elements.append(Paragraph("1. TOP CRIME HOTSPOTS & VULNERABILITY ZONES", h2_style))
    
    hotspot_rows = [
        [
            Paragraph("<b>Area Name</b>", cell_bold),
            Paragraph("<b>Risk Tier</b>", cell_bold),
            Paragraph("<b>Incidents</b>", cell_bold),
            Paragraph("<b>Primary Threat</b>", cell_bold),
            Paragraph("<b>Unsafe Time Slot</b>", cell_bold),
        ]
    ]

    for h in hotspot_areas[:8]:
        tier_color = '#dc2626' if h.get('alert_level') == 'red' else ('#d97706' if h.get('alert_level') == 'yellow' else '#16a34a')
        hotspot_rows.append([
            Paragraph(str(h.get('location_name', 'N/A')), cell_norm),
            Paragraph(f"<font color='{tier_color}'><b>{str(h.get('alert_level', 'green')).upper()}</b></font>", cell_norm),
            Paragraph(str(h.get('report_count', 0)), cell_norm),
            Paragraph(str(h.get('top_crime', 'General')), cell_norm),
            Paragraph(str(h.get('unsafe_time_slot', 'Night Hours')), cell_norm),
        ])

    if len(hotspot_rows) == 1:
        hotspot_rows.append([Paragraph("No active hotspot clusters detected.", cell_norm), Paragraph("-", cell_norm), Paragraph("-", cell_norm), Paragraph("-", cell_norm), Paragraph("-", cell_norm)])

    hotspot_table = Table(hotspot_rows, colWidths=[150, 75, 65, 125, 125])
    hotspot_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(hotspot_table)
    elements.append(Spacer(1, 14))

    # RECENT INCIDENTS TABLE
    elements.append(Paragraph("2. RECENT INCIDENT LOG", h2_style))
    
    rec_rows = [
        [
            Paragraph("<b>FIR Number</b>", cell_bold),
            Paragraph("<b>Crime Category</b>", cell_bold),
            Paragraph("<b>Location</b>", cell_bold),
            Paragraph("<b>Severity</b>", cell_bold),
            Paragraph("<b>Date & Time</b>", cell_bold),
            Paragraph("<b>Status</b>", cell_bold),
        ]
    ]

    for r in records[:10]:
        dt_str = (r.incident_datetime or r.date_time).strftime('%d %b %Y, %H:%M')
        rec_rows.append([
            Paragraph(r.fir_number, cell_norm),
            Paragraph(r.get_crime_type_display(), cell_norm),
            Paragraph(r.location_name[:20] if r.location_name else 'N/A', cell_norm),
            Paragraph(r.get_severity_level_display(), cell_norm),
            Paragraph(dt_str, cell_norm),
            Paragraph(r.get_status_display(), cell_norm),
        ])

    rec_table = Table(rec_rows, colWidths=[95, 95, 110, 75, 95, 70])
    rec_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(rec_table)
    elements.append(Spacer(1, 14))

    # FOOTER
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#94a3b8'), spaceBefore=6, spaceAfter=6))
    elements.append(Paragraph("Confidential - For Law Enforcement & Public Safety Administration Use Only.", sub_style))

    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="District_Crime_Bulletin_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response
