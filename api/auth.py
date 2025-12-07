"""
HMAC token authentication for ChoreBoard API.
"""
import hmac
import hashlib
import time
from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from users.models import User


class HMACAuthentication(BaseAuthentication):
    """
    HMAC-based authentication for public kiosk access.

    Token format: username:timestamp:signature
    Signature: HMAC-SHA256(username:timestamp, SECRET_KEY)
    Expiry: 24 hours from timestamp
    """

    TOKEN_EXPIRY_HOURS = 24

    def authenticate(self, request):
        """
        Authenticate the request using HMAC token.

        Returns:
            tuple: (user, token) if authentication successful
            None: if no token provided

        Raises:
            AuthenticationFailed: if token is invalid or expired
        """
        # Get token from header or query parameter
        token = request.META.get('HTTP_AUTHORIZATION', '')
        if token.startswith('Bearer '):
            token = token[7:]
        elif not token:
            token = request.query_params.get('token', '')

        if not token:
            return None  # No authentication attempted

        # Parse token
        try:
            username, timestamp_str, signature = token.split(':')
            timestamp = int(timestamp_str)
        except (ValueError, AttributeError):
            raise AuthenticationFailed('Invalid token format')

        # Verify timestamp (not expired)
        current_time = int(time.time())
        token_age_hours = (current_time - timestamp) / 3600

        if token_age_hours > self.TOKEN_EXPIRY_HOURS:
            raise AuthenticationFailed('Token expired')

        if token_age_hours < 0:
            raise AuthenticationFailed('Token timestamp is in the future')

        # Verify signature
        expected_signature = self._generate_signature(username, timestamp)
        if not hmac.compare_digest(signature, expected_signature):
            raise AuthenticationFailed('Invalid token signature')

        # Get user
        try:
            user = User.objects.get(username=username, is_active=True)
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found or inactive')

        return (user, token)

    @staticmethod
    def _generate_signature(username, timestamp):
        """Generate HMAC signature for username and timestamp."""
        message = f"{username}:{timestamp}".encode('utf-8')
        secret = settings.SECRET_KEY.encode('utf-8')
        signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
        return signature

    @staticmethod
    def generate_token(username):
        """
        Generate HMAC token for a user.

        Args:
            username: Username to generate token for

        Returns:
            str: HMAC token (username:timestamp:signature)
        """
        timestamp = int(time.time())
        signature = HMACAuthentication._generate_signature(username, timestamp)
        return f"{username}:{timestamp}:{signature}"

    def authenticate_header(self, request):
        """Return authentication scheme for WWW-Authenticate header."""
        return 'Bearer'


def generate_user_token(user):
    """
    Convenience function to generate HMAC token for a user.

    Args:
        user: User instance

    Returns:
        str: HMAC token
    """
    return HMACAuthentication.generate_token(user.username)
