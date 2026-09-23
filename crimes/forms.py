from django import forms
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from .models import CrimeRecord, CrimeAlert, PatrolSchedule


class CrimeRecordForm(forms.ModelForm):
    incident_datetime = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control',
            }
        ),
        label="Date & Time of Incident"
    )

    proof_file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'webp'])],
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png,.webp'}),
        label="Supporting Evidence / File"
    )

    class Meta:
        model = CrimeRecord
        fields = [
            'crime_type',
            'severity_level',
            'location_name',
            'landmark',
            'police_station',
            'incident_datetime',
            'weapon_involved',
            'victim_gender',
            'victim_age_group',
            'description',
            'proof_file',
            'latitude',
            'longitude',
        ]
        widgets = {
            'description': forms.Textarea(
                attrs={
                    'rows': 4,
                    'class': 'form-control',
                    'placeholder': 'Provide complete details: what happened, persons involved, loss of property, or sequence of events...'
                }
            ),
            'location_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'E.g. MG Road, Near Bus Stand, Sector 4'
                }
            ),
            'landmark': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'E.g. Opposite City Hospital, Behind Petrol Pump'
                }
            ),
            'police_station': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'E.g. Khargone Kotwali Police Station'
                }
            ),
            'weapon_involved': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'E.g. None, Knife, Firearm, Blunt Object'
                }
            ),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }

    def clean_proof_file(self):
        file = self.cleaned_data.get('proof_file')
        if file:
            # 5MB File Size Limit
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Supporting evidence file size cannot exceed 5 MB.")
        return file

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in ['latitude', 'longitude', 'incident_datetime', 'proof_file']:
                field.widget.attrs.setdefault('class', 'form-control')
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'

        if self.instance and self.instance.pk and self.instance.incident_datetime:
            self.initial['incident_datetime'] = self.instance.incident_datetime.strftime('%Y-%m-%dT%H:%M')
        elif not self.initial.get('incident_datetime'):
            self.initial['incident_datetime'] = timezone.now().strftime('%Y-%m-%dT%H:%M')


class FilterForm(forms.Form):
    crime_type = forms.ChoiceField(
        choices=[('', 'All Crime Types')] + list(CrimeRecord.CRIME_TYPES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    severity = forms.ChoiceField(
        choices=[('', 'All Severity Levels')] + list(CrimeRecord.SEVERITY_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    status = forms.ChoiceField(
        choices=[('', 'All Case Statuses')] + list(CrimeRecord.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Search FIR number, location or keyword...'}
        )
    )


class MLPredictForm(forms.Form):
    location_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'E.g. Sarafa Bazaar, Bus Stand Road, Zone 2'}
        )
    )

    latitude = forms.FloatField(
        required=True,
        widget=forms.NumberInput(
            attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': '21.824700'}
        )
    )

    longitude = forms.FloatField(
        required=True,
        widget=forms.NumberInput(
            attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': '75.610200'}
        )
    )

    target_datetime = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control'}
        )
    )

    incident_description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Optional: Paste suspected activity or crime narrative for NLP classification...'
            }
        )
    )


class CrimeAlertForm(forms.ModelForm):
    class Meta:
        model = CrimeAlert
        fields = ['title', 'alert_type', 'severity', 'location_name', 'message', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Alert Title (e.g. Night Snatching Warning)'}),
            'alert_type': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'location_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Target Sector or Landmark'}),
            'message': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Public safety advisory text...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class StatusUpdateForm(forms.ModelForm):
    class Meta:
        model = CrimeRecord
        fields = ['status', 'investigating_officer', 'admin_remark']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'investigating_officer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Officer Name / Badge #'}),
            'admin_remark': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Official investigation notes...'}),
        }


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'})
    )

    def clean_csv_file(self):
        file = self.cleaned_data.get('csv_file')
        if file:
            # 10MB File Size Limit
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("CSV file size cannot exceed 10 MB.")
        return file