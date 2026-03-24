from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls), #Depois trocar essa bagaça
    path('', include('clinica_app.urls')), 
]