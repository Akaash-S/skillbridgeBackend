import pytest
from unittest.mock import MagicMock, patch
from app import create_app

@pytest.fixture
def client():
    """Create a Flask test client with mock db allowed."""
    with patch.dict('os.environ', {'ALLOW_MOCK_DB': 'true', 'DISABLE_SCHEDULER': 'true'}):
        app = create_app()
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

def test_generate_roadmap_missing_target_role(client):
    """Test POST /roadmap/generate fails validation when targetRole is missing."""
    with patch('app.services.firebase_service.FirebaseAuthService.verify_token', return_value={'uid': 'test_user'}):
        response = client.post(
            '/roadmap/generate',
            json={},
            headers={'Authorization': 'Bearer valid_mock_token'}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 'VALIDATION_ERROR'
        assert 'targetRole' in data['error']

def test_generate_roadmap_invalid_experience_level(client):
    """Test POST /roadmap/generate fails validation when experienceLevel is invalid."""
    with patch('app.services.firebase_service.FirebaseAuthService.verify_token', return_value={'uid': 'test_user'}):
        response = client.post(
            '/roadmap/generate',
            json={'targetRole': 'frontend-developer', 'experienceLevel': 'super-expert'},
            headers={'Authorization': 'Bearer valid_mock_token'}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 'VALIDATION_ERROR'
        assert 'Must be one of' in data['error']

def test_generate_roadmap_success(client):
    """Test POST /roadmap/generate successfully creates and returns roadmap items."""
    mock_items = [
        {'id': 'item_1', 'skillId': 'javascript', 'skillName': 'JavaScript', 'completed': False}
    ]
    with patch('app.services.firebase_service.FirebaseAuthService.verify_token', return_value={'uid': 'test_user'}), \
         patch('app.services.roadmap_templates.FastRoadmapGenerator.generate_and_save_roadmap', return_value={'status': 'ok'}), \
         patch('app.services.user_state_manager.UserStateManager.get_user_state', return_value={'roadmapProgress': {'roadmapItems': mock_items}}):
        
        response = client.post(
            '/roadmap/generate',
            json={'targetRole': 'frontend-developer', 'experienceLevel': 'beginner'},
            headers={'Authorization': 'Bearer valid_mock_token'}
        )
        assert response.status_code == 201
        data = response.get_json()
        assert len(data) == 1
        assert data[0]['skillId'] == 'javascript'

def test_get_roadmap_unauthenticated(client):
    """Test GET /roadmap returns 401 when no auth credentials provided and Firebase is active."""
    with patch('app.services.firebase_service.FIREBASE_AVAILABLE', True):
        response = client.get('/roadmap')
        assert response.status_code == 401


def test_get_roadmap_no_active_roadmap(client):
    """Test GET /roadmap returns 200 with None when user has no active roadmap."""
    with patch('app.services.firebase_service.FirebaseAuthService.verify_token', return_value={'uid': 'test_user'}), \
         patch('app.db.firestore.FirestoreService.get_user_roadmap', return_value=None):
        
        response = client.get(
            '/roadmap',
            headers={'Authorization': 'Bearer valid_mock_token'}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['roadmap'] is None
        assert 'No active roadmap' in data['message']

def test_get_roadmap_templates(client):
    """Test GET /roadmap/templates returns pre-built templates without auth."""
    response = client.get('/roadmap/templates')
    assert response.status_code == 200
    data = response.get_json()
    assert 'templates' in data
    assert len(data['templates']) > 0
