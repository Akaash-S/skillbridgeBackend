from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import hashlib
import secrets
import string
import re

def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def hash_string(text: str) -> str:
    """Generate SHA-256 hash of a string"""
    return hashlib.sha256(text.encode()).hexdigest()

def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime object to string"""
    return dt.strftime(format_str)

def parse_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """Parse datetime string to datetime object"""
    try:
        return datetime.strptime(date_str, format_str)
    except ValueError:
        return None

def calculate_age_in_days(date: datetime) -> int:
    """Calculate age in days from a given date"""
    return (datetime.utcnow() - date).days

def is_recent(date: datetime, days: int = 7) -> bool:
    """Check if a date is within the last N days"""
    return calculate_age_in_days(date) <= days

def paginate_results(items: List[Any], page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    """Paginate a list of items"""
    total_items = len(items)
    total_pages = (total_items + per_page - 1) // per_page
    
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    
    paginated_items = items[start_index:end_index]
    
    return {
        'items': paginated_items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_items': total_items,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    }

def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """Extract keywords from text"""
    # Simple keyword extraction - remove common words and short words
    common_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
        'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
        'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
    }
    
    # Clean and split text
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    
    # Filter words
    keywords = [
        word for word in words 
        if len(word) >= min_length and word not in common_words
    ]
    
    # Remove duplicates while preserving order
    unique_keywords = []
    seen = set()
    for keyword in keywords:
        if keyword not in seen:
            unique_keywords.append(keyword)
            seen.add(keyword)
    
    return unique_keywords

def calculate_similarity_score(list1: List[str], list2: List[str]) -> float:
    """Calculate similarity score between two lists (Jaccard similarity)"""
    if not list1 and not list2:
        return 1.0
    
    set1 = set(item.lower() for item in list1)
    set2 = set(item.lower() for item in list2)
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0

def format_duration(hours: float) -> str:
    """Format duration in hours to human-readable string"""
    if hours < 1:
        minutes = int(hours * 60)
        return f"{minutes}m"
    elif hours < 24:
        return f"{hours:.1f}h"
    else:
        days = int(hours / 24)
        remaining_hours = hours % 24
        if remaining_hours == 0:
            return f"{days}d"
        else:
            return f"{days}d {remaining_hours:.1f}h"

def parse_duration(duration_str: str) -> float:
    """Parse duration string to hours (e.g., '2h 30m' -> 2.5)"""
    duration_str = duration_str.lower().strip()
    total_hours = 0.0
    
    # Match patterns like '2h', '30m', '1d', '2h 30m', etc.
    patterns = [
        (r'(\d+(?:\.\d+)?)d', 24),  # days
        (r'(\d+(?:\.\d+)?)h', 1),   # hours
        (r'(\d+(?:\.\d+)?)m', 1/60) # minutes
    ]
    
    for pattern, multiplier in patterns:
        matches = re.findall(pattern, duration_str)
        for match in matches:
            total_hours += float(match) * multiplier
    
    return total_hours

def generate_slug(text: str, max_length: int = 50) -> str:
    """Generate URL-friendly slug from text"""
    # Convert to lowercase and replace spaces with hyphens
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Limit length
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip('-')
    
    return slug

def calculate_readiness_score(matched_skills: int, partial_skills: int, total_required: int) -> float:
    """Calculate readiness score based on skill matching"""
    if total_required == 0:
        return 100.0
    
    # Weighted scoring: matched = 1.0, partial = 0.5
    weighted_score = (matched_skills * 1.0) + (partial_skills * 0.5)
    readiness_score = (weighted_score / total_required) * 100
    
    return min(100.0, max(0.0, readiness_score))

def group_by_key(items: List[Dict], key: str) -> Dict[str, List[Dict]]:
    """Group list of dictionaries by a specific key"""
    grouped = {}
    
    for item in items:
        group_key = item.get(key, 'unknown')
        if group_key not in grouped:
            grouped[group_key] = []
        grouped[group_key].append(item)
    
    return grouped

def sort_by_priority(items: List[Dict], priority_key: str = 'priority') -> List[Dict]:
    """Sort items by priority (high -> medium -> low)"""
    priority_order = {'high': 3, 'medium': 2, 'low': 1}
    
    return sorted(
        items,
        key=lambda x: priority_order.get(x.get(priority_key, 'medium'), 2),
        reverse=True
    )

def merge_dictionaries(dict1: Dict, dict2: Dict, deep: bool = True) -> Dict:
    """Merge two dictionaries, with dict2 values taking precedence"""
    if not deep:
        return {**dict1, **dict2}
    
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dictionaries(result[key], value, deep=True)
        else:
            result[key] = value
    
    return result

def validate_and_format_phone(phone: str, country_code: str = '+91') -> Optional[str]:
    """Validate and format phone number"""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Basic validation for Indian numbers (10 digits)
    if country_code == '+91' and len(digits) == 10:
        return f"+91{digits}"
    
    # Basic validation for US numbers (10 digits)
    if country_code == '+1' and len(digits) == 10:
        return f"+1{digits}"
    
    return None

def calculate_estimated_completion_time(milestones: List[Dict]) -> Dict[str, Any]:
    """Calculate estimated completion time for roadmap milestones"""
    total_weeks = 0
    total_hours = 0
    
    for milestone in milestones:
        milestone_weeks = milestone.get('estimatedWeeks', 2)
        total_weeks += milestone_weeks
        
        skills = milestone.get('skills', [])
        for skill in skills:
            skill_hours = skill.get('estimatedHours', 20)
            total_hours += skill_hours
    
    return {
        'totalWeeks': total_weeks,
        'totalHours': total_hours,
        'estimatedMonths': round(total_weeks / 4.33, 1),  # Average weeks per month
        'hoursPerWeek': round(total_hours / total_weeks, 1) if total_weeks > 0 else 0
    }

def format_currency(amount: float, currency: str = 'INR') -> str:
    """Format currency amount"""
    currency_symbols = {
        'INR': '₹',
        'USD': '$',
        'EUR': '€',
        'GBP': '£'
    }
    
    symbol = currency_symbols.get(currency, currency)
    
    if amount >= 10000000:  # 1 crore
        return f"{symbol}{amount/10000000:.1f}Cr"
    elif amount >= 100000:  # 1 lakh
        return f"{symbol}{amount/100000:.1f}L"
    elif amount >= 1000:
        return f"{symbol}{amount/1000:.1f}K"
    else:
        return f"{symbol}{amount:,.0f}"

def extract_skills_from_text(text: str, skill_database: List[str]) -> List[str]:
    """Extract skills mentioned in text based on skill database"""
    text_lower = text.lower()
    found_skills = []
    
    for skill in skill_database:
        skill_lower = skill.lower()
        
        # Check for exact match or skill as part of word boundary
        if re.search(r'\b' + re.escape(skill_lower) + r'\b', text_lower):
            found_skills.append(skill)
    
    return found_skills

def calculate_learning_streak(activity_dates: List[datetime]) -> int:
    """Calculate current learning streak in days"""
    if not activity_dates:
        return 0
    
    # Sort dates in descending order
    sorted_dates = sorted(activity_dates, reverse=True)
    
    # Check if there's activity today or yesterday
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    latest_date = sorted_dates[0].date()
    
    if latest_date not in [today, yesterday]:
        return 0
    
    # Count consecutive days
    streak = 1
    current_date = latest_date
    
    for i in range(1, len(sorted_dates)):
        next_date = sorted_dates[i].date()
        expected_date = current_date - timedelta(days=1)
        
        if next_date == expected_date:
            streak += 1
            current_date = next_date
        else:
            break
    
    return streak