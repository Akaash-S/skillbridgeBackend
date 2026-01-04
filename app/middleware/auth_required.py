from app.services.firebase_service import auth_required, optional_auth

# Re-export decorators for easy import
__all__ = ['auth_required', 'optional_auth']