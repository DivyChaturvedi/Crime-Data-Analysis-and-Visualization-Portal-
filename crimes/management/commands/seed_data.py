import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from crimes.models import CrimeRecord, CrimeAlert, PatrolSchedule

CRIME_TYPES = [
    'theft', 'assault', 'robbery', 'murder', 'kidnapping',
    'fraud', 'vandalism', 'cybercrime', 'domestic_violence', 'drug_trafficking',
]

SEVERITY_LEVELS = ['low', 'medium', 'high', 'critical']
STATUSES = ['pending', 'approved', 'investigating', 'resolved', 'closed']

# Real Khargone district localities with accurate coordinates
LOCATIONS = [
    ("Khargone City Center", 21.8234, 75.6150),
    ("Gandhi Chowk, Khargone", 21.8240, 75.6140),
    ("Kasba Ward, Khargone", 21.8250, 75.6170),
    ("Naya Bazaar, Khargone", 21.8210, 75.6130),
    ("Maheshwar Fort Road", 22.1760, 75.5880),
    ("Barwaha Main Market", 22.2560, 76.0370),
    ("Bhikangaon Square", 21.8750, 76.1580),
    ("Gogawan Bypass", 21.7780, 75.5380),
    ("Segaon Bus Stand", 21.8540, 75.4450),
    ("Sanawad Railway Crossing", 22.1800, 76.0670),
    ("Balwadi Naka", 21.8050, 75.7050),
    ("Mandleshwar Ghat", 22.1710, 75.6620),
    ("Kasrawad Highway", 22.0770, 75.6170),
    ("Jhirniya Tribal Belt", 22.0040, 75.4230),
    ("Old Bus Stand Khargone", 21.8225, 75.6155),
    ("Police Parade Ground", 21.8260, 75.6200),
    ("Collector Office Circle", 21.8245, 75.6190),
    ("Annapurna Nagar", 21.8195, 75.6125),
    ("Chhoti Kasba", 21.8235, 75.6145),
    ("Bistan Road", 21.8310, 75.6250),
]

NARRATIVES = {
    'theft': [
        "Complainant reports mobile phone snatched from pocket at crowded vegetable market.",
        "Hero Honda Splendor motorcycle stolen from outside temple premises during prayer hours.",
        "Gold necklace snatched from elderly woman on morning walk along ring road.",
        "Kirana store broken into at midnight, cash ₹15,000 and dry stock missing.",
        "Pickpocket incident reported at Khargone bus stand; leather wallet and Aadhaar card lost.",
    ],
    'assault': [
        "Victim attacked by group of three individuals over parking dispute, sustained head lacerations.",
        "Physical altercation between neighbours over water drainage boundary dispute.",
        "Shopkeeper assaulted during attempted extortion by known local troublemakers.",
        "Two motorists engaged in road rage incident near bypass junction with iron rods.",
        "Youth attacked at annual district mela grounds after heated argument.",
    ],
    'robbery': [
        "Armed individuals on black pulsar looted cash ₹45,000 from petrol pump cashier.",
        "Collection agent intercepted on highway and robbed of collection bag.",
        "Jewellery showroom shutter broken; silver ornaments and cash looted.",
        "Daylight robbery at grocery distributor premises; cash drawer emptied at knifepoint.",
        "Two masked individuals robbed a vegetable vendor on highway after midnight.",
    ],
    'murder': [
        "Unidentified deceased body discovered near canal embankment; sharp weapon trauma.",
        "Fatal property inheritance dispute escalated into physical violence.",
        "Suspicious death reported inside rented accommodation; forensic team deployed.",
        "Severe assault outside village dhaba resulted in fatal injury on arrival at hospital.",
        "Physical altercation turned deadly; accused apprehended at state border checkpost.",
    ],
    'kidnapping': [
        "Minor child reported missing while returning from tuition classes near Kasba.",
        "Family reported abduction of local merchant; extortion ransom call received.",
        "Attempted abduction of teenager foiled by quick action of nearby shopkeepers.",
        "Student missing after leaving college campus; phone switched off since morning.",
        "Young woman reported forcibly taken in four-wheeler near bypass highway.",
    ],
    'fraud': [
        "Complainant cheated of ₹1,20,000 in fake government solar pump subsidy scheme.",
        "Unauthorized biometric Aadhaar enabled payment transactions reported at CSC center.",
        "Agricultural land parcel sold fraudulently using counterfeit revenue stamps.",
        "Elderly pensioner defrauded by bogus life insurance bonus verification call.",
        "Fake employment offer letter issued for municipal corporation recruitment scam.",
    ],
    'vandalism': [
        "Public solar streetlights and battery enclosures vandalized and broken overnight.",
        "Boundary wall of government primary school damaged with heavy vehicle hit-and-run.",
        "Surveillance CCTV cameras installed at market intersection deliberately smashed.",
        "Public water filtration kiosk vandalized and copper piping severed.",
        "Bus shelter seating damaged during late night mob disturbance.",
    ],
    'cybercrime': [
        "Victim lost ₹65,000 after downloading fraudulent remote support screen-sharing APK.",
        "Social media profile cloned to solicit emergency money transfers from contacts.",
        "WhatsApp group admin reported circulation of morphed objectionable pictures.",
        "Online merchant portal account compromised; payment gateway redirected.",
        "Crypto investment scam: victim transferred ₹2,50,000 to unverified Telegram bot.",
    ],
    'domestic_violence': [
        "Complainant filed FIR regarding continuous physical torture and dowry harassment.",
        "Intervention requested by women helpline after domestic violence incident.",
        "Wife assaulted by intoxicated husband; medical examination conducted at Civil Hospital.",
        "Protection order violation and severe physical assault reported by complainant.",
        "Dowry demand and verbal harassment complaint registered under relevant sections.",
    ],
    'drug_trafficking': [
        "Special task force seized 14 kg contraband ganja concealed inside truck chassis.",
        "Opium syrup and banned psychotropic tablets recovered from illicit medical store.",
        "Drug courier intercepted at border barrier with commercial quantity of poppy straw.",
        "Illegal chemical distillation setup raided in rural outskirts; materials seized.",
        "Peddler arrested near educational institute carrying small packaging sachets.",
    ],
}

OFFICERS = [
    "Insp. Rameshwar Patel", "SI Sunita Sharma", "SI Anil Verma",
    "SI Kavita Joshi", "Insp. Mohan Yadav", "SI Deepak Tiwari",
    "SI Priya Malviya", "Insp. Vinod Rawat",
]

POLICE_STATIONS = [
    "Khargone Kotwali PS", "Maheshwar PS", "Barwaha PS",
    "Bhikangaon PS", "Sanawad PS", "Kasrawad PS",
    "Mandleshwar PS", "Gogawan PS",
]

WEAPONS = ['None', 'Knife', 'Iron Rod', 'Country Pistol', 'Stones', 'Acid/Chemical', 'Lathi']


class Command(BaseCommand):
    help = "Seed 70+ realistic CDAVP crime records, alerts, and patrol shifts for Khargone district"

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=70, help='Number of records to create')
        parser.add_argument('--flush', action='store_true', help='Delete existing crime records before seeding')

    def handle(self, *args, **options):
        count = options['count']
        flush = options['flush']

        if flush:
            deleted, _ = CrimeRecord.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Flushed {deleted} existing records."))

        # Create or fetch default administrative accounts
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@cdavp.gov.in',
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Command',
                'last_name': 'Administrator',
            }
        )
        admin_user.set_password('Admin@2026')
        admin_user.save()

        officer_user, _ = User.objects.get_or_create(
            username='officer1',
            defaults={
                'email': 'officer1@cdavp.gov.in',
                'is_staff': True,
                'is_superuser': False,
                'first_name': 'Rameshwar',
                'last_name': 'Patel',
            }
        )
        officer_user.set_password('Officer@2026')
        officer_user.save()

        citizen_user, _ = User.objects.get_or_create(
            username='citizen1',
            defaults={
                'email': 'citizen@cdavp.gov.in',
                'is_staff': False,
                'is_superuser': False,
                'first_name': 'Rajesh',
                'last_name': 'Kumar',
            }
        )
        citizen_user.set_password('Citizen@2026')
        citizen_user.save()

        now = timezone.now()
        records_created = 0

        # Temporal distribution across recent 12 months with high recency weight
        def random_date_biased():
            r = random.random()
            if r < 0.40:
                delta_days = random.randint(0, 30)
            elif r < 0.70:
                delta_days = random.randint(31, 90)
            else:
                delta_days = random.randint(91, 365)
            delta_hours = random.randint(0, 23)
            delta_minutes = random.randint(0, 59)
            return now - timedelta(days=delta_days, hours=delta_hours, minutes=delta_minutes)

        for i in range(count):
            crime_type = random.choice(CRIME_TYPES)
            location_name, lat, lng = random.choice(LOCATIONS)
            # Realistic spatial dispersion around sector
            lat += random.uniform(-0.012, 0.012)
            lng += random.uniform(-0.012, 0.012)

            severity = random.choice(SEVERITY_LEVELS)
            if crime_type in ('murder', 'kidnapping', 'drug_trafficking'):
                severity = random.choice(['high', 'critical'])
            elif crime_type in ('theft', 'vandalism', 'fraud'):
                severity = random.choice(['low', 'medium'])

            status = random.choices(
                STATUSES,
                weights=[20, 25, 30, 15, 10],
                k=1
            )[0]

            incident_dt = random_date_biased()
            description = random.choice(NARRATIVES[crime_type])
            officer = random.choice(OFFICERS)
            police_station = random.choice(POLICE_STATIONS)
            weapon = random.choice(WEAPONS)
            victim_age = random.choice(['child', 'youth', 'adult', 'senior', 'unknown'])
            victim_gender = random.choice(['male', 'female', 'unknown'])

            cr = CrimeRecord(
                crime_type=crime_type,
                description=description,
                location_name=location_name,
                latitude=round(lat, 6),
                longitude=round(lng, 6),
                severity_level=severity,
                status=status,
                incident_datetime=incident_dt,
                date_time=incident_dt,
                police_station=police_station,
                investigating_officer=officer,
                weapon_involved=weapon if weapon != 'None' else '',
                victim_gender=victim_gender,
                victim_age_group=victim_age,
                reported_by=citizen_user if random.random() > 0.3 else admin_user,
            )
            cr.save()
            # Update created_at timestamp
            CrimeRecord.objects.filter(pk=cr.pk).update(
                created_at=incident_dt + timedelta(hours=random.randint(1, 8))
            )
            records_created += 1

        # Seed Crime Alerts
        alerts_data = [
            ("High Security Alert: Night Robbery Patrols Intensified", "high_risk", "danger", "Special night checkpoints established across Khargone City Kotwali and Naya Bazaar after recent incidents.", "Khargone Kotwali Sector"),
            ("Advisory: Surge in Remote Banking APK Scams", "warning", "warning", "Do not download unverified APK files or grant screen access to callers claiming to be bank executives.", "District-Wide"),
            ("Special Night Patrolling Active in Maheshwar Ghats", "patrol", "info", "Sector PCR units on round-the-clock foot patrolling during tourist and pilgrim rush.", "Maheshwar Fort & Ghats"),
            ("Emergency AMBER Alert: Missing Child Search Operation", "emergency", "danger", "Search operation in progress around Barwaha bypass. Report any sightings to Control Room 100.", "Barwaha & NH-3 Corridor"),
            ("Traffic & Security Checkpoints on State Highway", "patrol", "info", "Routine vehicle inspection for documents and illegal freight active 24/7.", "Kasrawad Highway"),
        ]

        for title, alert_type, sev, msg, loc in alerts_data:
            if not CrimeAlert.objects.filter(title=title).exists():
                CrimeAlert.objects.create(
                    title=title,
                    alert_type=alert_type,
                    severity=sev,
                    message=msg,
                    location_name=loc,
                    created_by=admin_user,
                    is_active=True,
                )

        # Seed Patrol Schedules
        shifts = ['morning', 'evening', 'night']
        units = ['PCR Unit Alpha-1', 'Eagle Mobile-2', 'Cheetah Patrol-4', 'Hawk Squad-3', 'Tiger Unit-5']
        
        for idx, ps in enumerate(POLICE_STATIONS[:5]):
            shift = shifts[idx % len(shifts)]
            unit = units[idx % len(units)]
            if not PatrolSchedule.objects.filter(unit_name=unit, shift=shift).exists():
                PatrolSchedule.objects.create(
                    unit_name=unit,
                    assigned_area=f"{ps} Sector Patrol Zone",
                    shift=shift,
                    patrol_date=now.date(),
                    officer_in_charge=random.choice(OFFICERS),
                    contact_number=f"+91 9826{random.randint(100000, 999999)}",
                    status='active' if shift == 'evening' else 'scheduled',
                    notes="Intensive surveillance at major intersections, bank branches, and commercial markets.",
                )

        self.stdout.write(self.style.SUCCESS(
            f"\nSeeding Complete!\n"
            f"   - {records_created} crime records created\n"
            f"   - {CrimeAlert.objects.count()} active alerts configured\n"
            f"   - {PatrolSchedule.objects.count()} patrol shifts scheduled\n"
            f"\nDefault Credentials:\n"
            f"   admin / Admin@2026  (Super Administrator)\n"
            f"   officer1 / Officer@2026  (Police Staff Officer)\n"
            f"   citizen1 / Citizen@2026  (Registered Citizen)\n"
        ))
