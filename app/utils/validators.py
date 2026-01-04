import re
from typing import Dict, List, Any
from email_validator import validate_email as validate_email_format, EmailNotValidError

def validate_required_fields(data: Dict, required_fields: List[str]) -> bool:
    """Validate that all required fields are present and not empty"""
    if not data:
        return False
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            return False
    
    return True

def validate_email(email: str) -> bool:
    """Validate email format"""
    try:
        validate_email_format(email)
        return True
    except EmailNotValidError:
        return False

def validate_password(password: str) -> Dict[str, Any]:
    """
    Validate password strength
    Returns dict with 'valid' boolean and 'errors' list
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one number")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def validate_skill_level(level: str) -> bool:
    """Validate skill proficiency level"""
    valid_levels = ['beginner', 'intermediate', 'advanced']
    return level in valid_levels

def validate_experience_level(level: str) -> bool:
    """Validate user experience level"""
    valid_levels = ['beginner', 'intermediate', 'advanced']
    return level in valid_levels

def validate_confidence_level(confidence: str) -> bool:
    """Validate skill confidence level"""
    valid_confidence = ['low', 'medium', 'high']
    return confidence in valid_confidence

def validate_country_code(country_code: str) -> bool:
    """Validate country code (simplified validation)"""
    # Common country codes supported by Adzuna
    valid_codes = [
        'in', 'us', 'gb', 'ca', 'au', 'de', 'fr', 'nl', 'sg', 'za',
        'it', 'es', 'br', 'mx', 'pl', 'at', 'be', 'ch', 'nz'
    ]
    return country_code.lower() in valid_codes

def validate_url(url: str) -> bool:
    """Validate URL format"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None

def validate_json_structure(data: Dict, required_structure: Dict) -> Dict[str, Any]:
    """
    Validate JSON data against a required structure
    Returns dict with 'valid' boolean and 'errors' list
    """
    errors = []
    
    def check_structure(obj, structure, path=""):
        for key, expected_type in structure.items():
            current_path = f"{path}.{key}" if path else key
            
            if key not in obj:
                errors.append(f"Missing required field: {current_path}")
                continue
            
            value = obj[key]
            
            if isinstance(expected_type, type):
                if not isinstance(value, expected_type):
                    errors.append(f"Field {current_path} must be of type {expected_type.__name__}")
            elif isinstance(expected_type, dict):
                if isinstance(value, dict):
                    check_structure(value, expected_type, current_path)
                else:
                    errors.append(f"Field {current_path} must be an object")
            elif isinstance(expected_type, list) and len(expected_type) == 1:
                if isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(expected_type[0], type):
                            if not isinstance(item, expected_type[0]):
                                errors.append(f"Field {current_path}[{i}] must be of type {expected_type[0].__name__}")
                        elif isinstance(expected_type[0], dict):
                            check_structure(item, expected_type[0], f"{current_path}[{i}]")
                else:
                    errors.append(f"Field {current_path} must be an array")
    
    check_structure(data, required_structure)
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def sanitize_string(text: str, max_length: int = None) -> str:
    """Sanitize string input"""
    if not isinstance(text, str):
        return ""
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Remove potentially dangerous characters
    text = re.sub(r'[<>"\']', '', text)
    
    # Limit length if specified
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text

def validate_roadmap_data(roadmap_data: Dict) -> Dict[str, Any]:
    """Validate roadmap data structure"""
    required_structure = {
        'milestones': [
            {
                'title': str,
                'description': str,
                'order': int,
                'estimatedWeeks': int,
                'skills': [
                    {
                        'skillId': str,
                        'targetLevel': str,
                        'priority': str,
                        'estimatedHours': int
                    }
                ]
            }
        ]
    }
    
    result = validate_json_structure(roadmap_data, required_structure)
    
    # Additional validation for roadmap-specific rules
    if result['valid'] and 'milestones' in roadmap_data:
        for i, milestone in enumerate(roadmap_data['milestones']):
            # Validate skill levels
            if 'skills' in milestone:
                for j, skill in enumerate(milestone['skills']):
                    if 'targetLevel' in skill:
                        if not validate_skill_level(skill['targetLevel']):
                            result['errors'].append(f"Invalid targetLevel in milestone {i}, skill {j}")
                            result['valid'] = False
                    
                    if 'priority' in skill:
                        valid_priorities = ['low', 'medium', 'high']
                        if skill['priority'] not in valid_priorities:
                            result['errors'].append(f"Invalid priority in milestone {i}, skill {j}")
                            result['valid'] = False
    
    return result

def validate_learning_resource(resource_data: Dict) -> Dict[str, Any]:
    """Validate learning resource data"""
    required_structure = {
        'title': str,
        'url': str,
        'type': str,
        'level': str,
        'provider': str
    }
    
    result = validate_json_structure(resource_data, required_structure)
    
    # Additional validation
    if result['valid']:
        # Validate URL
        if 'url' in resource_data and not validate_url(resource_data['url']):
            result['errors'].append("Invalid URL format")
            result['valid'] = False
        
        # Validate resource type
        if 'type' in resource_data:
            valid_types = ['course', 'tutorial', 'documentation', 'video', 'book', 'article']
            if resource_data['type'] not in valid_types:
                result['errors'].append("Invalid resource type")
                result['valid'] = False
        
        # Validate level
        if 'level' in resource_data and not validate_skill_level(resource_data['level']):
            result['errors'].append("Invalid skill level")
            result['valid'] = False
    
    return result