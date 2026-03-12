from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('clinica_app.urls')), # Inclui as rotas do seu app
]