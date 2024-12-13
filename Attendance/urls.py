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
    HolidayViewSet,
    LeaveTypeViewSet,
    LeaveBalanceViewSet,
    LeaveRequestViewSet,
    auto_attend,
    AttendanceLogsViewSet,
    WorkedHoursViewSet,
)

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'activities', EmployeeActivityViewSet, basename='activity')
router.register(r'qr-codes', QRDetailsViewSet, basename='qr-code')
router.register(r'office-locations', OfficeLocationViewSet, basename='office-location')
router.register(r'holidays', HolidayViewSet, basename='holiday')
router.register(r'leave-types', LeaveTypeViewSet, basename='leave-type')
router.register(r'leave-balances', LeaveBalanceViewSet, basename='leave-balance')
router.register(r'leave-requests', LeaveRequestViewSet, basename='leave-request')
router.register(r'attendance-logs', AttendanceLogsViewSet, basename='attendance-logs')
router.register(r'worked-hours', WorkedHoursViewSet, basename='worked-hours')

# First add the registration URL, then include router URLs
urlpatterns = [
    path('register/', register, name='register'),
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),
    path('', include(router.urls)),
    path('generate-qr/<str:usage_type>/', generate_qr, name='generate_qr'),
    path('attend/', mark_attendance, name='mark_attendance'),
    path('auto-attend/', auto_attend, name='auto_attend'),
] 