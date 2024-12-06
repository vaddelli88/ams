from django.core.management.base import BaseCommand
from Attendance.models import Employee
import uuid
from getpass import getpass
from django.core.exceptions import ValidationError

class Command(BaseCommand):
    help = 'Create a superuser employee'

    def add_arguments(self, parser):
        # Add any additional arguments if needed
        pass

    def handle(self, *args, **options):
        try:
            # Get input from command line
            self.stdout.write('\nCreating superuser employee...\n')
            email = input('Email: ').strip()
            username = input('Username: ').strip()
            first_name = input('First name: ').strip()
            last_name = input('Last name: ').strip()
            
            # Get password with confirmation
            while True:
                password = getpass('Password: ')
                password_confirm = getpass('Password (again): ')
                
                if password != password_confirm:
                    self.stdout.write(self.style.ERROR('Passwords do not match. Please try again.'))
                    continue
                
                if len(password) < 6:
                    self.stdout.write(self.style.ERROR('Password must be at least 6 characters long.'))
                    continue
                
                break

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
                f'\nSuperuser employee created successfully!\n'
                f'Employee ID: {superuser.employee_id}\n'
                f'Email: {superuser.email}\n'
                f'Username: {superuser.username}'
            ))

        except KeyboardInterrupt:
            self.stdout.write('\nOperation cancelled.')
            return
        except ValidationError as e:
            self.stdout.write(self.style.ERROR(f'Validation error: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {str(e)}')) 