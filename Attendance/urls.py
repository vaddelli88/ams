from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmployeeViewSet, 
    EmployeeActivityViewSet, 
    QRDetailsViewSet,
    register,
    login,
    logout,
    generate_qr,
    mark_attendance,
    OfficeLocationViewSet,
)

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'activities', EmployeeActivityViewSet, basename='activity')
router.register(r'qr-codes', QRDetailsViewSet, basename='qr-code')
router.register(r'office-locations', OfficeLocationViewSet, basename='office-location')

# First add the registration URL, then include router URLs
urlpatterns = [
    path('register/', register, name='register'),
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),
    path('', include(router.urls)),
    path('generate-qr/<str:usage_type>/', generate_qr, name='generate_qr'),
    path('attend/', mark_attendance, name='mark_attendance'),
] 