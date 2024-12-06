from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, parser_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import (
    Employee, 
    EmployeeActivity, 
    QRDetails,
    OutstandingTokenModel,  # Use our custom models
    BlacklistedTokenModel   # Use our custom models
)
from .serializers import EmployeeSerializer, EmployeeActivitySerializer, QRDetailsSerializer
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
        QRDetails.objects.filter(
            usage_type=usage_type,
            is_valid=True
        ).update(is_valid=False)

        # Generate unique number
        while True:
            unique_number = str(uuid.uuid4())[:8].upper()
            if not QRDetails.objects.filter(unique_number=unique_number).exists():
                break

        # Create QR code record
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
        
        # The URL that will be encoded in QR
        qr_url = f"http://{request.get_host()}/attend?code={unique_number}&type={usage_type}"
        qr.add_data(qr_url)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        # Create response with appropriate headers
        response = HttpResponse(buffer.getvalue(), content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="{usage_type}_qr_{unique_number}.png"'
        
        return response

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def mark_attendance(request):
    """
    Handle attendance marking from QR code scans
    Expects:
    Query parameters:
        - code: The unique QR code
        - type: 'check-in' or 'check-out'
    Request body:
        - employee_id: Employee's ID
        - location: Location of attendance
    """
    try:
        # Get QR parameters from query
        code = request.query_params.get('code')
        usage_type = request.query_params.get('type')

        # Get employee details from request body
        employee_id = request.data.get('employee_id')
        location = request.data.get('location')

        # Validate required fields
        if not all([code, usage_type, employee_id, location]):
            return Response({
                'error': 'Missing required fields',
                'required': {
                    'code': bool(code),
                    'type': bool(usage_type),
                    'employee_id': bool(employee_id),
                    'location': bool(location)
                }
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

        # Check if employee has already marked attendance for this type today
        today = datetime.now().date()
        existing_activity = EmployeeActivity.objects.filter(
            emp=employee,
            activity=usage_type,
            timestamp__date=today
        ).exists()

        if existing_activity:
            return Response({
                'error': f'Already marked {usage_type} for today'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create attendance record
        activity = EmployeeActivity.objects.create(
            emp=employee,
            activity=usage_type,
            location=location,
            timestamp=datetime.now()  # Current timestamp
        )

        # Invalidate QR code after use
        qr_detail.is_valid = False
        qr_detail.save()

        return Response({
            'message': f'Attendance {usage_type} marked successfully',
            'details': {
                'employee_id': employee.employee_id,
                'location': activity.location,
                'timestamp': activity.timestamp,
                'activity': activity.activity
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
