from rest_framework_simplejwt.tokens import Token, AccessToken, RefreshToken
from rest_framework_simplejwt.models import TokenUser
from datetime import datetime, timedelta, timezone
from django.conf import settings
import uuid
from .models import OutstandingTokenModel, BlacklistedTokenModel
from django.utils import timezone as django_timezone
from rest_framework_simplejwt.tokens import TokenError

class CustomRefreshToken(RefreshToken):
    lifetime = timedelta(days=36500)  # 100 years

    def __init__(self, token=None, verify=True):
        super().__init__(token, verify=False)  # Skip JWT validation
        self._access_token = None
        
        if token is not None:
            try:
                self.payload = self.token_backend.decode(token, verify=False)
            except Exception as e:
                print(f"Token decode error: {str(e)}")
                raise TokenError(str(e))

    @property
    def access_token(self):
        """Get the access token."""
        if self._access_token is None:
            self._access_token = self._create_access_token()
        return self._access_token

    def _create_access_token(self):
        """Create a new access token."""
        access = self.__class__()
        
        # Set required claims
        now = django_timezone.now()
        exp = now + self.lifetime
        
        # Generate access token payload
        access.payload = {
            'token_type': 'access',
            'exp': datetime.timestamp(exp),
            'iat': datetime.timestamp(now),
            'jti': str(uuid.uuid4()),
            'employee_id': self.payload.get('employee_id', None),
            'type': 'access'
        }

        # Store access token in database
        OutstandingTokenModel.objects.create(
            user_id=self.payload.get('employee_id'),
            jti=access.payload['jti'],
            token=str(access),
            created_at=now,
            expires_at=exp.replace(microsecond=0)
        )

        return access

    @classmethod
    def for_user(cls, user):
        """Create a new token for a user."""
        token = cls()
        
        # Set required claims
        now = django_timezone.now()
        exp = now + cls.lifetime
        
        # Generate token payload
        token.payload = {
            'token_type': 'refresh',
            'exp': datetime.timestamp(exp),
            'iat': datetime.timestamp(now),
            'jti': str(uuid.uuid4()),
            'employee_id': user.employee_id,
            'type': 'refresh'
        }

        # Store token in database
        OutstandingTokenModel.objects.create(
            user_id=user.employee_id,
            jti=token.payload['jti'],
            token=str(token),
            created_at=now,
            expires_at=exp.replace(microsecond=0)
        )
        
        return token

    def blacklist(self):
        """Blacklist the token."""
        try:
            # Get token from database using JTI
            outstanding_token = OutstandingTokenModel.objects.get(
                jti=self.payload['jti']
            )
            
            # Create blacklist record
            return BlacklistedTokenModel.objects.create(token=outstanding_token)
            
        except OutstandingTokenModel.DoesNotExist:
            raise TokenError('Token not found in database')
        except Exception as e:
            print(f"Blacklist error: {str(e)}")
            raise

    def __getitem__(self, key):
        return self.payload[key]

    def __setitem__(self, key, value):
        self.payload[key] = value