from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from rest_framework_simplejwt.tokens import Token

class EmployeeManager(BaseUserManager):
    def create_user(self, employee_id, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(employee_id=employee_id, email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, employee_id, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(employee_id, email, username, password, **extra_fields)

    def get_by_natural_key(self, login_value):
        """
        Enable authentication by employee_id, email, or username
        """
        try:
            return self.get(
                models.Q(employee_id=login_value) |
                models.Q(email=login_value) |
                models.Q(username=login_value)
            )
        except self.model.DoesNotExist:
            return None

class Employee(AbstractBaseUser, PermissionsMixin):
    id = models.AutoField(primary_key=True)
    employee_id = models.CharField(max_length=6, unique=True)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(db_column='is_super', default=False)
    is_staff = models.BooleanField(default=False)

    objects = EmployeeManager()

    USERNAME_FIELD = 'employee_id'
    REQUIRED_FIELDS = ['email', 'username']

    class Meta:
        db_table = 'employee'
        managed = False

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

class EmployeeActivity(models.Model):
    ACTIVITY_CHOICES = [
        ('check-in', 'Check In'),
        ('check-out', 'Check Out'),
    ]
    
    id = models.AutoField(primary_key=True)
    emp = models.ForeignKey(Employee, to_field='employee_id', db_column='emp_id', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    activity = models.CharField(max_length=9, choices=ACTIVITY_CHOICES)

    class Meta:
        db_table = 'employee_activity'
        managed = False

class QRDetails(models.Model):
    USAGE_CHOICES = [
        ('check-in', 'Check In'),
        ('check-out', 'Check Out'),
    ]
    
    id = models.AutoField(primary_key=True)
    unique_number = models.CharField(max_length=255, unique=True)
    usage_type = models.CharField(max_length=9, choices=USAGE_CHOICES)
    is_valid = models.BooleanField(default=True)
    create_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'qr_details'
        managed = False

class OutstandingTokenModel(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        Employee,
        to_field='employee_id',
        db_column='employee_id',
        on_delete=models.CASCADE
    )
    jti = models.CharField(unique=True, max_length=255)
    token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'token_blacklist_outstandingtoken'
        managed = False

class BlacklistedTokenModel(models.Model):
    id = models.AutoField(primary_key=True)
    token = models.OneToOneField(
        OutstandingTokenModel,
        on_delete=models.CASCADE,
        db_column='token_id'
    )
    blacklisted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'token_blacklist_blacklistedtoken'
        managed = False

class OfficeLocation(models.Model):
    id = models.AutoField(primary_key=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    is_valid = models.BooleanField(default=True)

    class Meta:
        db_table = 'office_location'
        managed = False

class WorkedHours(models.Model):
    id = models.AutoField(primary_key=True)
    emp = models.ForeignKey(Employee, to_field='employee_id', db_column='employee_id', on_delete=models.CASCADE)
    work_date = models.DateField()
    worked_hours = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        db_table = 'worked_hours'
        managed = False

class Holiday(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    date = models.DateField()
    description = models.TextField(null=True, blank=True)
    is_company_holiday = models.BooleanField(default=True)  # True for company, False for public holidays

    class Meta:
        db_table = 'holidays'
        managed = False

class LeaveType(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)  # e.g., Sick, Vacation
    description = models.TextField(null=True, blank=True)
    max_days_per_year = models.IntegerField()

    class Meta:
        db_table = 'leave_types'
        managed = False

class LeaveBalance(models.Model):
    id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, to_field='employee_id', db_column='employee_id', on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.IntegerField()
    balance = models.DecimalField(max_digits=5, decimal_places=2)
    used = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = 'leave_balances'
        managed = False

class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ]

    id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, to_field='employee_id', db_column='employee_id', on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    applied_on = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(Employee, to_field='employee_id', db_column='approved_by', 
                                  related_name='approved_leaves', null=True, blank=True, 
                                  on_delete=models.SET_NULL)
    response_on = models.DateTimeField(null=True, blank=True)
    response_note = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'leave_requests'
        managed = False
