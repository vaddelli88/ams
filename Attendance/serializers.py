from rest_framework import serializers
from .models import Employee, EmployeeActivity, QRDetails, OfficeLocation, Holiday, LeaveType, LeaveBalance, LeaveRequest, WorkedHours

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            'id', 
            'employee_id', 
            'email', 
            'username', 
            'first_name', 
            'last_name',
            'date_joined',
            'is_active',
            'is_staff',
            'is_superuser'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

class EmployeeActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeActivity
        fields = ['id', 'emp', 'timestamp', 'activity']
        read_only_fields = ['timestamp']

class QRDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = QRDetails
        fields = ['id', 'unique_number', 'usage_type', 'is_valid', 'create_date']
        read_only_fields = ['create_date']

class OfficeLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficeLocation
        fields = ['id', 'latitude', 'longitude', 'is_valid'] 

class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ['id', 'name', 'date', 'description', 'is_company_holiday']

class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'name', 'description', 'max_days_per_year']

class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    
    class Meta:
        model = LeaveBalance
        fields = ['id', 'employee', 'leave_type', 'leave_type_name', 'year', 'balance', 'used']

class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.username', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee', 'employee_name', 
            'leave_type', 'leave_type_name',
            'start_date', 'end_date', 'reason',
            'status', 'applied_on',
            'approved_by', 'approved_by_name',
            'response_on', 'response_note'
        ]
        read_only_fields = ['status', 'applied_on', 'approved_by', 'response_on'] 

class WorkedHoursSerializer(serializers.ModelSerializer):
    employee_id = serializers.CharField(source='emp.employee_id', read_only=True)
    username = serializers.CharField(source='emp.username', read_only=True)

    class Meta:
        model = WorkedHours
        fields = ['work_date', 'worked_hours', 'employee_id', 'username']