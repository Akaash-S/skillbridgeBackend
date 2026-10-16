import pytest
from unittest.mock import MagicMock, patch
from app.services.skills_engine import SkillsEngine

@pytest.fixture
def skills_engine():
    """Fixture providing a SkillsEngine with a mocked FirestoreService."""
    with patch('app.services.skills_engine.FirestoreService') as mock_db_class:
        mock_db_instance = MagicMock()
        mock_db_class.return_value = mock_db_instance
        engine = SkillsEngine()
        engine.db_service = mock_db_instance
        yield engine

def test_analyze_skills_for_role_full_match(skills_engine):
    """Test 100% readiness when user has all required skills at or above target levels."""
    uid = "user_test_1"
    role_id = "backend-developer"

    role_mock = {
        'roleId': role_id,
        'title': 'Backend Developer',
        'requiredSkills': [
            {'skillId': 'python', 'minProficiency': 'intermediate'},
            {'skillId': 'sql', 'minProficiency': 'beginner'}
        ]
    }

    user_skills_mock = [
        {'skillId': 'python', 'name': 'Python', 'category': 'Backend', 'userLevel': 'advanced', 'userConfidence': 'high'},
        {'skillId': 'sql', 'name': 'SQL', 'category': 'Database', 'userLevel': 'intermediate', 'userConfidence': 'high'}
    ]

    skills_engine.db_service.query_collection.side_effect = lambda collection, filters: [role_mock] if collection == 'job_roles' else []
    skills_engine.get_user_skills = MagicMock(return_value=user_skills_mock)

    result = skills_engine.analyze_skills_for_role(uid, role_id)

    assert result is not None
    assert result['roleId'] == role_id
    assert result['roleTitle'] == 'Backend Developer'
    assert result['totalRequired'] == 2
    assert result['matchedCount'] == 2
    assert result['partialCount'] == 0
    assert result['missingCount'] == 0
    assert result['readinessScore'] == 100.0
    assert len(result['matchedSkills']) == 2
    assert len(result['partialSkills']) == 0
    assert len(result['missingSkills']) == 0

def test_analyze_skills_for_role_all_partial(skills_engine):
    """Test 50% readiness when user possesses all skills but below required proficiency."""
    uid = "user_test_2"
    role_id = "frontend-developer"

    role_mock = {
        'roleId': role_id,
        'title': 'Frontend Developer',
        'requiredSkills': [
            {'skillId': 'react', 'minProficiency': 'intermediate'},
            {'skillId': 'typescript', 'minProficiency': 'advanced'}
        ]
    }

    # User is beginner for both (below intermediate and below advanced)
    user_skills_mock = [
        {'skillId': 'react', 'name': 'React', 'category': 'Frontend', 'userLevel': 'beginner', 'userConfidence': 'medium'},
        {'skillId': 'typescript', 'name': 'TypeScript', 'category': 'Frontend', 'userLevel': 'intermediate', 'userConfidence': 'medium'}
    ]

    skills_engine.db_service.query_collection.side_effect = lambda collection, filters: [role_mock] if collection == 'job_roles' else []
    skills_engine.get_user_skills = MagicMock(return_value=user_skills_mock)

    result = skills_engine.analyze_skills_for_role(uid, role_id)

    assert result is not None
    assert result['totalRequired'] == 2
    assert result['matchedCount'] == 0
    assert result['partialCount'] == 2
    assert result['missingCount'] == 0
    # Each partial skill counts for 0.5 weight: (2 * 0.5) / 2 * 100 = 50.0%
    assert result['readinessScore'] == 50.0
    assert result['partialSkills'][0]['gap'] == "beginner → intermediate"
    assert result['partialSkills'][1]['gap'] == "intermediate → advanced"

def test_analyze_skills_for_role_all_missing(skills_engine):
    """Test 0% readiness when user has none of the required skills."""
    uid = "user_test_3"
    role_id = "devops-engineer"

    role_mock = {
        'roleId': role_id,
        'title': 'DevOps Engineer',
        'requiredSkills': [
            {'skillId': 'docker', 'minProficiency': 'intermediate'},
            {'skillId': 'kubernetes', 'minProficiency': 'intermediate'}
        ]
    }

    skills_engine.db_service.query_collection.side_effect = lambda collection, filters: [role_mock] if collection == 'job_roles' else []
    skills_engine.get_user_skills = MagicMock(return_value=[])

    result = skills_engine.analyze_skills_for_role(uid, role_id)

    assert result is not None
    assert result['totalRequired'] == 2
    assert result['matchedCount'] == 0
    assert result['partialCount'] == 0
    assert result['missingCount'] == 2
    assert result['readinessScore'] == 0.0
    assert len(result['missingSkills']) == 2
    assert result['missingSkills'][0]['skillId'] == 'docker'
    assert result['missingSkills'][1]['skillId'] == 'kubernetes'

def test_analyze_skills_for_role_mixed_classification(skills_engine):
    """Test mixed classification: matched, partial, and missing skills."""
    uid = "user_test_4"
    role_id = "fullstack-developer"

    role_mock = {
        'roleId': role_id,
        'title': 'Full Stack Developer',
        'requiredSkills': [
            {'skillId': 'python', 'minProficiency': 'intermediate'},   # User has advanced -> Matched (1.0)
            {'skillId': 'sql', 'minProficiency': 'intermediate'},      # User has intermediate -> Matched (1.0)
            {'skillId': 'docker', 'minProficiency': 'intermediate'},   # User has beginner -> Partial (0.5)
            {'skillId': 'aws', 'minProficiency': 'beginner'}           # User missing -> Missing (0.0)
        ]
    }

    user_skills_mock = [
        {'skillId': 'python', 'name': 'Python', 'category': 'Backend', 'userLevel': 'advanced', 'userConfidence': 'high'},
        {'skillId': 'sql', 'name': 'SQL', 'category': 'Database', 'userLevel': 'intermediate', 'userConfidence': 'high'},
        {'skillId': 'docker', 'name': 'Docker', 'category': 'DevOps', 'userLevel': 'beginner', 'userConfidence': 'medium'}
    ]

    skills_engine.db_service.query_collection.side_effect = lambda collection, filters: [role_mock] if collection == 'job_roles' else []
    skills_engine.get_user_skills = MagicMock(return_value=user_skills_mock)

    result = skills_engine.analyze_skills_for_role(uid, role_id)

    assert result is not None
    assert result['totalRequired'] == 4
    assert result['matchedCount'] == 2
    assert result['partialCount'] == 1
    assert result['missingCount'] == 1
    # Readiness score calculation: (2 matched + 1 partial * 0.5) / 4 * 100 = 2.5 / 4 * 100 = 62.5%
    assert result['readinessScore'] == 62.5

def test_analyze_skills_for_role_empty_requirements(skills_engine):
    """Test edge case where role has empty requiredSkills list."""
    uid = "user_test_5"
    role_id = "general-intern"

    role_mock = {
        'roleId': role_id,
        'title': 'General Intern',
        'requiredSkills': []
    }

    skills_engine.db_service.query_collection.side_effect = lambda collection, filters: [role_mock] if collection == 'job_roles' else []
    skills_engine.get_user_skills = MagicMock(return_value=[])

    result = skills_engine.analyze_skills_for_role(uid, role_id)

    assert result is not None
    assert result['totalRequired'] == 0
    assert result['readinessScore'] == 100
    assert result['matchedSkills'] == []
    assert result['partialSkills'] == []
    assert result['missingSkills'] == []

def test_analyze_skills_for_role_not_found(skills_engine):
    """Test returns None when roleId does not exist in job_roles collection."""
    uid = "user_test_6"
    role_id = "non-existent-role"

    skills_engine.db_service.query_collection.return_value = []
    skills_engine.get_user_skills = MagicMock(return_value=[])

    result = skills_engine.analyze_skills_for_role(uid, role_id)
    assert result is None
