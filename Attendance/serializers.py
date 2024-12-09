from rest_framework import serializers
from .models import Employee, EmployeeActivity, QRDetails, OfficeLocation

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