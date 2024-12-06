from django.core.management.base import BaseCommand
from Attendance.models import Employee
import uuid

class Command(BaseCommand):
    help = 'Create a superuser'

    def handle(self, *args, **options):
        try:
            # Get input from command line
            email = input('Email: ')
            username = input('Username: ')
            first_name = input('First name: ')
            last_name = input('Last name: ')
            password = input('Password: ')

            # Generate unique employee_id
            while True:
                employee_id = f"EMP{str(uuid.uuid4())[:3].upper()}"
                if not Employee.objects.filter(employee_id=employee_id).exists():
                    break

            # Create superuser with generated employee_id
            superuser = Employee.objects.create_superuser(
                employee_id=employee_id,  # Auto-generated
                email=email,
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            self.stdout.write(self.style.SUCCESS(
                f'\nSuperuser created successfully!\n'
                f'Employee ID: {superuser.employee_id}\n'
                f'Email: {superuser.email}\n'
                f'Username: {superuser.username}'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {str(e)}')) 