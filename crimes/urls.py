from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alias'),
    path('ai-analytics/', views.ai_analytics_view, name='ai_analytics'),
    path('map/', views.map_view, name='map_view'),
    
    # Crimes CRUD
    path('crimes/', views.crime_list, name='crime_list'),
    path('crimes/add/', views.crime_add, name='crime_add'),
    path('crimes/<int:pk>/', views.crime_detail, name='crime_detail'),
    path('crimes/edit/<int:pk>/', views.crime_edit, name='crime_edit'),
    path('crimes/delete/<int:pk>/', views.crime_delete, name='crime_delete'),
    
    # Reports & Exports
    path('crimes/<int:pk>/pdf/', views.download_fir_pdf, name='download_fir_pdf'),
    path('reports/bulletin/pdf/', views.download_bulletin_pdf, name='download_bulletin_pdf'),
    path('crimes/upload/', views.csv_upload, name='csv_upload'),
    path('crimes/export/csv/', views.csv_export, name='csv_export'),
    
    # Alerts & Bulletins
    path('alerts/', views.alerts_view, name='alerts_view'),
    
    # Admin Panel & Command Controls
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/update-status/<int:pk>/<str:new_status>/', views.admin_update_status, name='admin_update_status'),
    path('admin-panel/retrain-ml/', views.admin_retrain_ml, name='admin_retrain_ml'),
    
    # APIs
    path('api/crimes/', views.crime_api, name='crime_api'),
    path('api/ml/predict/', views.api_ml_predict, name='api_ml_predict'),
    path('api/ml/classify-text/', views.api_ml_classify_text, name='api_ml_classify_text'),
]
