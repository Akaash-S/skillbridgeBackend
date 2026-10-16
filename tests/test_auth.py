import pytest
from unittest.mock import MagicMock, patch
from app import create_app

@pytest.fixture
def client():
    """Create a Flask test client with mock db allowed and scheduler disabled."""
    with patch.dict('os.environ', {'ALLOW_MOCK_DB': 'true', 'DISABLE_SCHEDULER': 'true'}):
        app = create_app()
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

def test_login_missing_id_token(client):
    """Test POST /auth/login returns 400 when idToken is missing."""
    response = client.post('/auth/login', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data['code'] == 'VALIDATION_ERROR'
    assert 'idToken' in data['error']

def test_login_invalid_token(client):
    """Test POST /auth/login returns 401 when Firebase token is invalid or expired."""
    with patch('app.services.firebase_service.FirebaseAuthService.verify_token', return_value=None):
        response = client.post('/auth/login', json={'idToken': 'expired_or_fake_token'})
        assert response.status_code == 401
        data = response.get_json()
        assert data['code'] == 'AUTH_TOKEN_INVALID'

def test_login_success_sets_http_only_cookie(client):
    """Test POST /auth/login with valid token creates session and sets httpOnly cookie."""
    mock_user = {
        'uid': 'user_123',
        'email': 'user@example.com',
        'name': 'Test User'
    }
    with patch('app.services.firebase_service.FirebaseAuthService.verify_token', return_value={'uid': 'user_123'}), \
         patch('app.db.firestore.FirestoreService.get_document', return_value=mock_user), \
         patch('app.db.firestore.FirestoreService.update_document', return_value=True), \
         patch('app.db.firestore.FirestoreService.log_user_activity', return_value=True):

        response = client.post('/auth/login', json={'idToken': 'valid_firebase_id_token'})
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Login successful'
        assert data['user']['uid'] == 'user_123'
        
        # Verify Set-Cookie header contains sb_session and HttpOnly
        cookie_header = response.headers.get('Set-Cookie', '')
        assert 'sb_session' in cookie_header
        assert 'HttpOnly' in cookie_header

def test_me_unauthenticated(client):
    """Test GET /auth/me returns 401 when unauthenticated and Firebase is enabled."""
    with patch('app.services.firebase_service.FIREBASE_AVAILABLE', True):
        response = client.get('/auth/me')
        assert response.status_code == 401

def test_me_authenticated(client):
    """Test GET /auth/me returns current user profile when valid token provided."""
    mock_user = {'uid': 'user_123', 'email': 'user@example.com', 'name': 'Test User'}
    with patch('app.services.firebase_service.FIREBASE_AVAILABLE', True), \
         patch('app.services.firebase_service.FirebaseAuthService.extract_token_from_request', return_value='valid_token'), \
         patch('app.services.firebase_service.FirebaseAuthService.verify_token', return_value={'uid': 'user_123'}), \
         patch('app.db.firestore.FirestoreService.get_document', return_value=mock_user):

        response = client.get('/auth/me', headers={'Authorization': 'Bearer valid_token'})
        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['uid'] == 'user_123'

def test_logout_clears_session_cookie(client):
    """Test POST /auth/logout clears the httpOnly session cookie."""
    response = client.post('/auth/logout')
    assert response.status_code == 200
    cookie_header = response.headers.get('Set-Cookie', '')
    assert 'sb_session' in cookie_header
    assert 'Max-Age=0' in cookie_header or 'expires=' in cookie_header.lower()
