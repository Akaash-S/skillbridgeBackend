import requests
from app.config import Config
from app.db.firestore import FirestoreService
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class JobsService:
    """Job search and caching service using Adzuna API"""
    
    def __init__(self):
        self.db_service = FirestoreService()
        self.app_id = Config.ADZUNA_APP_ID
        self.app_key = Config.ADZUNA_APP_KEY
        self.base_url = "https://api.adzuna.com/v1/api/jobs"
        self.cache_duration_hours = 6  # Cache jobs for 6 hours
    
    def search_jobs(self, role: str, country: str = 'in', location: str = None, limit: int = 20) -> Dict:
        """Search for jobs using Adzuna API with optimized caching"""
        try:
            # Normalize search parameters for better caching
            role_normalized = role.strip().lower()
            country_normalized = country.lower()
            
            # Check cache first with normalized key
            cache_key = f"{role_normalized.replace(' ', '_')}_{country_normalized}"
            cached_jobs = self._get_cached_jobs(cache_key, role)
            if cached_jobs and len(cached_jobs.get('jobs', [])) > 0:
                logger.info(f"Cache hit for {role} in {country} ({len(cached_jobs['jobs'])} jobs)")
                return {
                    'jobs': cached_jobs['jobs'][:limit],
                    'source': 'cache',
                    'total': len(cached_jobs['jobs']),
                    'cachedAt': cached_jobs['cachedAt'],
                    'searchTerm': role
                }
            
            # Fetch from Adzuna API with optimized parameters
            jobs_data = self._fetch_from_adzuna(role, country, location, min(limit * 2, 50))  # Fetch more for better results
            
            if jobs_data and 'results' in jobs_data and len(jobs_data['results']) > 0:
                # Process and format jobs with enhanced data
                formatted_jobs = self._format_jobs(jobs_data['results'])
                
                # Cache the results with normalized key
                self._cache_jobs(cache_key, role, formatted_jobs)
                
                logger.info(f"API fetch for {role} in {country}: {len(formatted_jobs)} jobs in cache")
                
                return {
                    'jobs': formatted_jobs[:limit],
                    'source': 'api',
                    'total': jobs_data.get('count', len(formatted_jobs)),
                    'searchTerm': role
                }
            else:
                logger.warning(f"No jobs found for {role} in {country}")
                return {
                    'jobs': [],
                    'source': 'api',
                    'total': 0,
                    'searchTerm': role
                }
                
        except Exception as e:
            logger.error(f"Error searching jobs for {role}: {str(e)}")
            return {
                'jobs': [],
                'source': 'error',
                'total': 0,
                'error': str(e),
                'searchTerm': role
            }
    
    def _fetch_from_adzuna(self, role: str, country: str, location: str = None, limit: int = 20) -> Optional[Dict]:
        """Fetch jobs from Adzuna API"""
        try:
            url = f"{self.base_url}/{country}/search/1"
            
            params = {
                'app_id': self.app_id,
                'app_key': self.app_key,
                'what': role,
                'results_per_page': min(limit, 50),  # Adzuna max is 50
                'sort_by': 'relevance'
            }
            
            if location:
                params['where'] = location
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Adzuna API request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error fetching from Adzuna: {str(e)}")
            return None
    
    def _format_jobs(self, raw_jobs: List[Dict]) -> List[Dict]:
        """Format raw Adzuna job data"""
        formatted_jobs = []
        
        for job in raw_jobs:
            try:
                # Extract skills from description (simple keyword matching)
                description = job.get('description', '').lower()
                skills = self._extract_skills_from_description(description)
                
                formatted_job = {
                    'jobId': job.get('id', ''),
                    'title': job.get('title', ''),
                    'company': job.get('company', {}).get('display_name', ''),
                    'location': self._format_location(job.get('location', {})),
                    'description': job.get('description', '')[:500] + '...' if len(job.get('description', '')) > 500 else job.get('description', ''),
                    'salary': self._format_salary(job.get('salary_min'), job.get('salary_max')),
                    'skills': skills,
                    'applyUrl': job.get('redirect_url', ''),
                    'postedDate': job.get('created', ''),
                    'category': job.get('category', {}).get('label', ''),
                    'contractType': job.get('contract_type', ''),
                    'source': 'adzuna'
                }
                
                formatted_jobs.append(formatted_job)
                
            except Exception as e:
                logger.warning(f"Error formatting job: {str(e)}")
                continue
        
        return formatted_jobs
    
    def _extract_skills_from_description(self, description: str) -> List[str]:
        """Extract technical skills from job description"""
        # Common technical skills to look for
        skill_keywords = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
            'node.js', 'express', 'django', 'flask', 'spring', 'html', 'css',
            'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'docker', 'kubernetes',
            'aws', 'azure', 'gcp', 'git', 'jenkins', 'terraform', 'ansible',
            'machine learning', 'ai', 'tensorflow', 'pytorch', 'pandas', 'numpy',
            'rest api', 'graphql', 'microservices', 'agile', 'scrum', 'devops'
        ]
        
        found_skills = []
        for skill in skill_keywords:
            if skill.lower() in description:
                found_skills.append(skill)
        
        return found_skills[:10]  # Limit to 10 skills
    
    def _format_location(self, location_data: Dict) -> str:
        """Format location from Adzuna data"""
        if not location_data:
            return ''
        
        parts = []
        if location_data.get('display_name'):
            parts.append(location_data['display_name'])
        elif location_data.get('area'):
            if isinstance(location_data['area'], list) and location_data['area']:
                parts.extend(location_data['area'])
        
        return ', '.join(parts) if parts else ''
    
    def _format_salary(self, salary_min: float, salary_max: float) -> Dict:
        """Format salary information"""
        if not salary_min and not salary_max:
            return {'display': 'Not specified', 'min': None, 'max': None}
        
        if salary_min and salary_max:
            return {
                'display': f'₹{salary_min:,.0f} - ₹{salary_max:,.0f}',
                'min': salary_min,
                'max': salary_max
            }
        elif salary_min:
            return {
                'display': f'₹{salary_min:,.0f}+',
                'min': salary_min,
                'max': None
            }
        else:
            return {
                'display': f'Up to ₹{salary_max:,.0f}',
                'min': None,
                'max': salary_max
            }
    
    def _get_cached_jobs(self, cache_key: str, original_role: str) -> Optional[Dict]:
        """Get cached jobs if still valid with normalized cache key"""
        try:
            cached_data = self.db_service.get_document('jobs_cache', cache_key)
            
            if not cached_data:
                return None
            
            # Check if cache is still valid (reduced to 3 minutes for faster updates)
            cached_at = cached_data.get('cachedAt')
            if cached_at:
                # Ensure both datetimes are timezone-aware or naive
                if hasattr(cached_at, 'tzinfo') and cached_at.tzinfo is not None:
                    from datetime import timezone
                    current_time = datetime.now(timezone.utc)
                else:
                    current_time = datetime.utcnow()
                
                cache_age = current_time - cached_at
                # Reduced cache duration to 3 minutes for faster updates
                if cache_age < timedelta(minutes=3):
                    return cached_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached jobs for {original_role}: {str(e)}")
            return None
    
    def _cache_jobs(self, cache_key: str, original_role: str, jobs: List[Dict]):
        """Cache job search results with normalized key"""
        try:
            cache_data = {
                'role': original_role,
                'normalizedKey': cache_key,
                'jobs': jobs,
                'cachedAt': datetime.utcnow(),
                'jobCount': len(jobs)
            }
            
            self.db_service.create_document('jobs_cache', cache_key, cache_data)
            logger.info(f"Cached {len(jobs)} jobs for {original_role} (key: {cache_key})")
            
        except Exception as e:
            logger.error(f"Error caching jobs for {original_role}: {str(e)}")
    
    def get_job_recommendations(self, uid: str, limit: int = 10) -> List[Dict]:
        """Get job recommendations based on user profile and skills"""
        try:
            # Get user profile
            user_profile = self.db_service.get_document('users', uid)
            if not user_profile:
                return []
            
            career_goal = user_profile.get('careerGoal', '')
            if not career_goal:
                return []
            
            # Get user skills
            user_skills = self.db_service.get_user_skills(uid)
            user_skill_names = [skill.get('skillId', '') for skill in user_skills]
            
            # Search for jobs matching career goal
            job_results = self.search_jobs(career_goal, limit=limit * 2)  # Get more to filter
            jobs = job_results.get('jobs', [])
            
            # Score jobs based on skill match
            scored_jobs = []
            for job in jobs:
                job_skills = job.get('skills', [])
                
                # Calculate skill match score
                matching_skills = set(user_skill_names) & set(job_skills)
                skill_match_score = len(matching_skills) / max(len(job_skills), 1) if job_skills else 0
                
                job_with_score = {
                    **job,
                    'matchScore': skill_match_score,
                    'matchingSkills': list(matching_skills),
                    'recommendationReason': f'Matches your {career_goal} career goal'
                }
                scored_jobs.append(job_with_score)
            
            # Sort by match score and return top results
            scored_jobs.sort(key=lambda x: x['matchScore'], reverse=True)
            
            return scored_jobs[:limit]
            
        except Exception as e:
            logger.error(f"Error getting job recommendations: {str(e)}")
            return []
    
    def get_trending_roles(self, country: str = 'in') -> List[Dict]:
        """Get trending job roles (simplified implementation)"""
        try:
            # Predefined trending roles for tech industry
            trending_roles = [
                'Software Engineer',
                'Data Scientist',
                'Frontend Developer',
                'Backend Developer',
                'DevOps Engineer',
                'Machine Learning Engineer',
                'Product Manager',
                'UI/UX Designer'
            ]
            
            role_stats = []
            
            for role in trending_roles:
                try:
                    # Get job count for each role
                    job_results = self.search_jobs(role, country, limit=1)
                    job_count = job_results.get('total', 0)
                    
                    role_stats.append({
                        'role': role,
                        'jobCount': job_count,
                        'trend': 'up' if job_count > 50 else 'stable'  # Simplified trend
                    })
                    
                except Exception as e:
                    logger.warning(f"Error getting stats for role {role}: {str(e)}")
                    continue
            
            # Sort by job count
            role_stats.sort(key=lambda x: x['jobCount'], reverse=True)
            
            return role_stats
            
        except Exception as e:
            logger.error(f"Error getting trending roles: {str(e)}")
            return []
    
