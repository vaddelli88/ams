from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, parser_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import (
    Employee, 
    EmployeeActivity, 
    QRDetails,
    OutstandingTokenModel,  # Use our custom models
    BlacklistedTokenModel,   # Use our custom models
    OfficeLocation,
    WorkedHours
)
from .serializers import EmployeeSerializer, EmployeeActivitySerializer, QRDetailsSerializer, OfficeLocationSerializer
import uuid
from django.contrib.auth import authenticate
from .tokens import CustomRefreshToken
from rest_framework_simplejwt.tokens import TokenError
import qrcode
from io import BytesIO
from django.http import HttpResponse
from django.core.files.base import ContentFile
import os
from django.conf import settings
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from decimal import Decimal
from django.db.models import Q
from datetime import datetime, timedelta
from django.utils import timezone

# Create your views here.

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'employee_id'

    @action(detail=True, methods=['post'])
    def check_in(self, request, employee_id=None):
        try:
            employee = self.get_object()
            activity = EmployeeActivity.objects.create(
                emp=employee,
                activity='check-in'
            )
            serializer = EmployeeActivitySerializer(activity)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def check_out(self, request, employee_id=None):
        try:
            employee = self.get_object()
            activity = EmployeeActivity.objects.create(
                emp=employee,
                activity='check-out'
            )
            serializer = EmployeeActivitySerializer(activity)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class EmployeeActivityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EmployeeActivity.objects.all()
    serializer_class = EmployeeActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_super:
            queryset = queryset.filter(emp=self.request.user)
        return queryset

class QRDetailsViewSet(viewsets.ModelViewSet):
    queryset = QRDetails.objects.all()
    serializer_class = QRDetailsSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def validate_qr(self, request, pk=None):
        qr_detail = self.get_object()
        if not qr_detail.is_valid:
            return Response(
                {'error': 'QR code is invalid or expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create activity based on QR type
        activity = EmployeeActivity.objects.create(
            emp=request.user,
            activity=qr_detail.usage_type
        )
        
        # Invalidate QR code after use
        qr_detail.is_valid = False
        qr_detail.save()
        
        return Response(
            EmployeeActivitySerializer(activity).data,
            status=status.HTTP_200_OK
        )

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def register(request):
    """
    Register a new employee in the system.
    
    Methods:
        POST
        
    Required Fields:
        - email
        - username
        - first_name
        - last_name
        - password
        
    Returns:
        - Success: Employee details and message
        - Error: Error message with details
        
    Validation:
        - Unique username and email
        - Unique employee_id (auto-generated)
    """
    data = request.data.copy()
    
    # Check for required fields
    required_fields = ['email', 'username', 'first_name', 'last_name', 'password']
    
    for field in required_fields:
        if field not in data:
            return Response(
                {"error": f"{field} is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Check if username or email already exists
    if Employee.objects.filter(username=data['username']).exists():
        return Response(
            {"error": "Username already exists"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if Employee.objects.filter(email=data['email']).exists():
        return Response(
            {"error": "Email already exists"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Generate a unique employee_id (6 characters)
        while True:
            employee_id = f"EMP{str(uuid.uuid4())[:3].upper()}"
            if not Employee.objects.filter(employee_id=employee_id).exists():
                break
        
        # Create employee
        employee = Employee.objects.create_user(
            employee_id=employee_id,
            email=data['email'],
            username=data['username'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name']
        )
        
        # Create serializer instance with the employee
        serializer = EmployeeSerializer(employee)
        
        return Response({
            'message': 'Employee registered successfully',
            'employee': serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['POST'])
def login(request):
    login = request.data.get('login')
    password = request.data.get('password')
    
    if not login or not password:
        return Response(
            {'error': 'Both login and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = Employee.objects.get_by_natural_key(login)
    if user and user.check_password(password):
        # Create refresh token
        refresh = CustomRefreshToken.for_user(user)
        
        response_data = {
            'message': 'Login successful',
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            },
            'user': {
                'id': user.id,
                'employee_id': user.employee_id,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'last_activity': None
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    else:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        print("Starting logout process...")
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            print("No refresh token provided")
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        print(f"Got refresh token: {refresh_token[:30]}...")
        
        # Decode token to get JTI
        token = CustomRefreshToken(refresh_token)
        jti = token.payload.get('jti')
        
        print(f"Token JTI: {jti}")
        
        # Check token in database
        try:
            outstanding_token = OutstandingTokenModel.objects.get(jti=jti)
            print(f"Found token in database with id: {outstanding_token.id}")
            
            # Check if already blacklisted
            if BlacklistedTokenModel.objects.filter(token=outstanding_token).exists():
                return Response(
                    {'error': 'Token is already blacklisted'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Blacklist the token
            blacklisted = BlacklistedTokenModel.objects.create(token=outstanding_token)
            print(f"Token blacklisted with id: {blacklisted.id}")
            
            return Response({
                'message': 'Logout successful',
                'blacklisted_token_id': blacklisted.id
            }, status=status.HTTP_200_OK)
            
        except OutstandingTokenModel.DoesNotExist:
            print(f"Token with JTI {jti} not found in database")
            return Response(
                {'error': 'Token not found in database'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        print(f"Logout error: {str(e)}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_qr(request, usage_type):
    """
    Generate QR code for check-in/check-out
    usage_type should be either 'check-in' or 'check-out'
    """
    try:
        # Verify user is staff or superuser
        if not request.user.is_staff and not request.user.is_superuser:
            return Response(
                {'error': 'You do not have permission to generate QR codes'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate usage type
        if usage_type not in ['check-in', 'check-out']:
            return Response(
                {'error': 'Invalid usage type. Must be check-in or check-out'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Invalidate previous QR codes of the same type
        invalidated_count = QRDetails.objects.filter(
            usage_type=usage_type,
            is_valid=True
        ).update(is_valid=False)

        print(f"Invalidated {invalidated_count} previous {usage_type} QR codes")

        # Generate unique number
        while True:
            unique_number = str(uuid.uuid4())[:8].upper()
            if not QRDetails.objects.filter(unique_number=unique_number).exists():
                break

        # Create new QR code record
        qr_detail = QRDetails.objects.create(
            unique_number=unique_number,
            usage_type=usage_type,
            is_valid=True
        )

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        qr_url = f"http://{request.get_host()}/attend?code={unique_number}&type={usage_type}"
        qr.add_data(qr_url)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        # Create response
        response = HttpResponse(buffer.getvalue(), content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="{usage_type}_qr_{unique_number}.png"'
        
        return response

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points using Haversine formula
    Returns distance in meters
    """
    R = 6371000  # Earth's radius in meters

    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance

def get_last_activity(employee):
    """Get employee's last activity for validation"""
    return EmployeeActivity.objects.filter(
        emp=employee
    ).order_by('-timestamp').first()

def calculate_worked_hours(check_in_time, check_out_time):
    """
    Calculate hours worked between check-in and check-out
    Returns time in HH.MM format (e.g., 8.30 for 8 hours 30 minutes)
    """
    # Make both times timezone-aware if they aren't already
    if check_in_time.tzinfo is None:
        check_in_time = check_in_time.replace(tzinfo=timezone.utc)
    if check_out_time.tzinfo is None:
        check_out_time = check_out_time.replace(tzinfo=timezone.utc)
        
    time_diff = check_out_time - check_in_time
    total_minutes = time_diff.total_seconds() / 60  # Convert to minutes
    
    hours = int(total_minutes // 60)  # Get complete hours
    minutes = int(total_minutes % 60)  # Get remaining minutes
    
    # Convert to HH.MM format
    decimal_time = Decimal(f"{hours}.{minutes:02d}")  # :02d ensures two digits for minutes
    return decimal_time

def handle_missing_checkout(employee, last_activity):
    """Handle cases where employee didn't check out from previous day"""
    if last_activity and last_activity.activity == 'check-in':
        # Get the date of last activity
        last_date = last_activity.timestamp.date()
        
        # If last check-in was not today and no checkout was recorded
        if last_date < datetime.now().date():
            # Add default 2 hours for incomplete previous day
            WorkedHours.objects.create(
                emp=employee,
                work_date=last_date,
                worked_hours=Decimal('2.00')  # Default 2 hours for incomplete checkout
            )
            return True
    return False

@api_view(['POST'])
def mark_attendance(request):
    try:
        # Get QR parameters from query
        code = request.query_params.get('code')
        usage_type = request.query_params.get('type')

        # Get employee details and location from request body
        employee_id = request.data.get('employee_id')
        current_latitude = request.data.get('latitude')
        current_longitude = request.data.get('longitude')

        # Validate required fields
        if not all([code, usage_type, employee_id, current_latitude, current_longitude]):
            return Response({
                'error': 'Missing required fields',
                'required': {
                    'code': bool(code),
                    'type': bool(usage_type),
                    'employee_id': bool(employee_id),
                    'latitude': bool(current_latitude),
                    'longitude': bool(current_longitude)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get valid office location
        office_location = OfficeLocation.objects.filter(is_valid=True).first()
        if not office_location:
            return Response({
                'error': 'No valid office location found'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Calculate distance
        distance = calculate_distance(
            float(current_latitude),
            float(current_longitude),
            float(office_location.latitude),
            float(office_location.longitude)
        )

        # Check if within 200 meters
        if distance > 200:
            return Response({
                'error': 'You are too far from the office location',
                'distance': f'{distance:.2f} meters',
                'max_allowed': '200 meters'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate QR code
        qr_detail = QRDetails.objects.filter(
            unique_number=code,
            usage_type=usage_type,
            is_valid=True
        ).first()

        if not qr_detail:
            return Response({
                'error': 'Invalid or expired QR code'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate employee
        try:
            employee = Employee.objects.get(employee_id=employee_id)
        except Employee.DoesNotExist:
            return Response({
                'error': f'Employee with ID {employee_id} not found'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get employee's last activity
        last_activity = get_last_activity(employee)
        today = datetime.now().date()

        # Modified activity sequence validation
        if last_activity:
            if usage_type == 'check-in':
                if last_activity.activity == 'check-in':
                    return Response({
                        'error': 'Cannot check in: You have not checked out from your previous session',
                        'last_activity': {
                            'type': last_activity.activity,
                            'timestamp': last_activity.timestamp
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)
                # If last activity was check-out, allow new check-in
            elif usage_type == 'check-out':
                if last_activity.activity == 'check-out':
                    return Response({
                        'error': 'Cannot check out: You have not checked in yet',
                        'last_activity': {
                            'type': last_activity.activity,
                            'timestamp': last_activity.timestamp
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)
        elif usage_type == 'check-out':
            return Response({
                'error': 'Cannot check out: No previous check-in found'
            }, status=status.HTTP_400_BAD_REQUEST)

        # For check-out, calculate and store worked hours
        if usage_type == 'check-out':
            # Get today's last check-in
            check_in = EmployeeActivity.objects.filter(
                emp=employee,
                activity='check-in',
                timestamp__date=today
            ).order_by('-timestamp').first()

            if check_in:
                # Calculate worked hours for this session
                current_time = timezone.now()
                session_hours = calculate_worked_hours(check_in.timestamp, current_time)
                
                # Get or create today's worked hours record
                worked_hours_record, created = WorkedHours.objects.get_or_create(
                    emp=employee,
                    work_date=today,
                    defaults={'worked_hours': Decimal('0.00')}
                )

                # Add current session hours to total
                total_minutes = (
                    int(str(worked_hours_record.worked_hours).split('.')[0]) * 60 +  # Hours to minutes
                    int(str(worked_hours_record.worked_hours).split('.')[1])         # Minutes
                ) + (
                    int(str(session_hours).split('.')[0]) * 60 +                     # Session hours to minutes
                    int(str(session_hours).split('.')[1])                            # Session minutes
                )

                # Convert total minutes back to HH.MM format
                total_hours = int(total_minutes // 60)
                total_minutes = int(total_minutes % 60)
                worked_hours_record.worked_hours = Decimal(f"{total_hours}.{total_minutes:02d}")
                worked_hours_record.save()

                # Create check-out record
                activity = EmployeeActivity.objects.create(
                    emp=employee,
                    activity=usage_type,
                    timestamp=current_time
                )

                return Response({
                    'message': f'Attendance {usage_type} marked successfully',
                    'details': {
                        'employee_id': employee.employee_id,
                        'timestamp': activity.timestamp,
                        'activity': activity.activity,
                        'distance_from_office': f'{distance:.2f} meters',
                        'session_hours': str(session_hours),
                        'total_worked_hours': str(worked_hours_record.worked_hours)
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'No check-in record found for today'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Regular check-in process
            activity = EmployeeActivity.objects.create(
                emp=employee,
                activity=usage_type,
                timestamp=timezone.now()
            )

            return Response({
                'message': f'Attendance {usage_type} marked successfully',
                'details': {
                    'employee_id': employee.employee_id,
                    'timestamp': activity.timestamp,
                    'activity': activity.activity,
                    'distance_from_office': f'{distance:.2f} meters'
                }
            }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Add this new permission class
class IsSuperuserOrStaff(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and (request.user.is_superuser or request.user.is_staff))

class OfficeLocationViewSet(viewsets.ModelViewSet):
    queryset = OfficeLocation.objects.all()
    serializer_class = OfficeLocationSerializer

    def get_permissions(self):
        """
        Only allow superusers and staff to manage office locations
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsSuperuserOrStaff()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        """
        Create a new office location and invalidate previous locations
        """
        try:
            # Validate required fields
            latitude = request.data.get('latitude')
            longitude = request.data.get('longitude')

            if not latitude or not longitude:
                return Response({
                    'error': 'Both latitude and longitude are required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Invalidate previous locations
            OfficeLocation.objects.filter(is_valid=True).update(is_valid=False)

            # Create new location
            location = OfficeLocation.objects.create(
                latitude=latitude,
                longitude=longitude,
                is_valid=True
            )

            serializer = self.get_serializer(location)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        """
        List all office locations, with option to filter valid ones
        """
        valid_only = request.query_params.get('valid_only', 'false').lower() == 'true'
        queryset = self.get_queryset()
        
        if valid_only:
            queryset = queryset.filter(is_valid=True)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """
        Toggle the validity status of a location
        """
        location = self.get_object()
        location.is_valid = not location.is_valid
        location.save()

        return Response({
            'message': f'Location status updated to {"valid" if location.is_valid else "invalid"}',
            'location': self.get_serializer(location).data
        })
