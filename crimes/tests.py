import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from crimes.models import CrimeRecord, CrimeAlert, PatrolSchedule, MLPredictionLog
from crimes.ml_engine import predict_incident_features, compute_spatial_clusters, calculate_risk_probability
from crimes.reports import generate_fir_pdf, generate_bulletin_pdf


class CrimeModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testofficer', password='password123', is_staff=True)

    def test_crime_record_creation_and_fir_generation(self):
        crime = CrimeRecord.objects.create(
            crime_type='theft',
            description='Motorcycle stolen from public parking',
            location_name='Gandhi Chowk',
            latitude=21.824,
            longitude=75.614,
            severity_level='medium',
            status='pending',
            reported_by=self.user,
        )
        self.assertTrue(crime.fir_number.startswith('FIR-'))
        self.assertEqual(crime.crime_type, 'theft')
        self.assertIn('Gandhi Chowk', str(crime))

    def test_crime_alert_creation(self):
        alert = CrimeAlert.objects.create(
            title='Test Alert Title',
            alert_type='warning',
            severity='warning',
            message='Test alert broadcast message',
            location_name='Khargone Central',
            created_by=self.user,
        )
        self.assertEqual(alert.title, 'Test Alert Title')
        self.assertTrue(alert.is_active)


class MLEngineTests(TestCase):
    def test_text_classification(self):
        result = predict_incident_features("Armed men with firearms snatched gold jewelry and cash at gunpoint")
        self.assertIn('predicted_crime_type', result)
        self.assertIn('predicted_severity', result)
        self.assertIn('confidence', result)
        self.assertGreaterEqual(result['confidence'], 0.0)

    def test_risk_probability(self):
        risk = calculate_risk_probability(21.8234, 75.6150)
        self.assertIn('risk_score', risk)
        self.assertIn('risk_level', risk)
        self.assertIn('predicted_primary_threat', risk)
        self.assertGreaterEqual(risk['risk_score'], 0.0)
        self.assertLessEqual(risk['risk_score'], 100.0)

    def test_spatial_clustering(self):
        user = User.objects.create_user(username='clusteruser', password='password123')
        for i in range(5):
            CrimeRecord.objects.create(
                crime_type='theft',
                description=f'Incident {i} near market',
                location_name='Gandhi Chowk',
                latitude=21.824 + (i * 0.001),
                longitude=75.614 + (i * 0.001),
                severity_level='medium',
                status='approved',
                reported_by=user,
            )
        records = CrimeRecord.objects.filter(status='approved')
        clusters = compute_spatial_clusters(records)
        self.assertIsInstance(clusters, list)


class PDFGenerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pdfuser', password='password123')
        self.crime = CrimeRecord.objects.create(
            crime_type='robbery',
            description='Robbery incident at grocery store with iron rod',
            location_name='Naya Bazaar',
            latitude=21.821,
            longitude=75.613,
            severity_level='high',
            status='approved',
            reported_by=self.user,
        )

    def test_fir_pdf_generation(self):
        response = generate_fir_pdf(self.crime)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(len(response.content) > 500)
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_bulletin_pdf_generation(self):
        records = CrimeRecord.objects.filter(status='approved')
        clusters = compute_spatial_clusters(records)
        alert_summary = {'red_count': 1, 'yellow_count': 0, 'green_count': 0}
        response = generate_bulletin_pdf(records, alert_summary, clusters)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(len(response.content) > 500)
        self.assertTrue(response.content.startswith(b'%PDF'))


class ViewsAndAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username='superadmin', password='password123', email='admin@test.com')
        self.client.force_login(self.admin)
        self.crime = CrimeRecord.objects.create(
            crime_type='assault',
            description='Physical dispute outside local market',
            location_name='Kasba Ward',
            latitude=21.825,
            longitude=75.617,
            severity_level='medium',
            status='approved',
            reported_by=self.admin,
        )

    def test_public_and_auth_pages(self):
        # Dashboard
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)

        # Map View
        resp = self.client.get(reverse('map_view'))
        self.assertEqual(resp.status_code, 200)

        # AI Analytics
        resp = self.client.get(reverse('ai_analytics'))
        self.assertEqual(resp.status_code, 200)

        # Alerts
        resp = self.client.get(reverse('alerts_view'))
        self.assertEqual(resp.status_code, 200)

        # Crime List
        resp = self.client.get(reverse('crime_list'))
        self.assertEqual(resp.status_code, 200)

        # Crime Detail
        resp = self.client.get(reverse('crime_detail', args=[self.crime.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_api_ml_predict(self):
        resp = self.client.get(reverse('api_ml_predict'), {'lat': 21.824, 'lng': 75.614})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('risk_score', data.get('data', {}))

    def test_api_ml_classify_text(self):
        resp = self.client.get(reverse('api_ml_classify_text'), {'text': 'Shoplifting at bus terminal'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('predicted_crime_type', data.get('data', {}))

    def test_fir_pdf_download_view(self):
        resp = self.client.get(reverse('download_fir_pdf', args=[self.crime.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_bulletin_pdf_download_view(self):
        resp = self.client.get(reverse('download_bulletin_pdf'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_csv_export_view(self):
        resp = self.client.get(reverse('csv_export'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
