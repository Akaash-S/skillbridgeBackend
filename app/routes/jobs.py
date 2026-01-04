from flask import Blueprint, request, jsonify
from app.middleware.auth_required import auth_required, optional_auth
from app.services.jobs_service import JobsService
import logging

logger = logging.getLogger(__name__)
jobs_bp = Blueprint('jobs', __name__)
jobs_service = JobsService()

@jobs_bp.route('/search', methods=['GET'])
@optional_auth
def search_jobs():
    """
    Search for jobs
    Query params:
    - role: job role/title (required)
    - country: country code (optional, default: 'in')
    - location: specific location (optional)
    - limit: number of results (optional, default: 20)
    """
    try:
        role = request.args.get('role')
        if not role:
            return jsonify({
                'error': 'Missing required parameter: role',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        country = request.args.get('country', 'in')
        location = request.args.get('location')
        limit = int(request.args.get('limit', 20))
        
        # Validate limit
        if limit < 1 or limit > 100:
            return jsonify({
                'error': 'Limit must be between 1 and 100',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        # Search jobs
        results = jobs_service.search_jobs(role, country, location, limit)
        
        return jsonify({
            'query': {
                'role': role,
                'country': country,
                'location': location,
                'limit': limit
            },
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Search jobs error: {str(e)}")
        return jsonify({
            'error': 'Failed to search jobs',
            'code': 'SEARCH_JOBS_ERROR'
        }), 500

@jobs_bp.route('/recommendations', methods=['GET'])
@auth_required
def get_job_recommendations():
    """
    Get personalized job recommendations for authenticated user
    Query params:
    - limit: number of results (optional, default: 10)
    """
    try:
        uid = request.current_user['uid']
        limit = int(request.args.get('limit', 10))
        
        # Validate limit
        if limit < 1 or limit > 50:
            return jsonify({
                'error': 'Limit must be between 1 and 50',
                'code': 'VALIDATION_ERROR'
            }), 400
        
        recommendations = jobs_service.get_job_recommendations(uid, limit)
        
        return jsonify({
            'recommendations': recommendations,
            'count': len(recommendations)
        }), 200
        
    except Exception as e:
        logger.error(f"Get job recommendations error: {str(e)}")
        return jsonify({
            'error': 'Failed to get job recommendations',
            'code': 'GET_RECOMMENDATIONS_ERROR'
        }), 500

@jobs_bp.route('/trending', methods=['GET'])
@optional_auth
def get_trending_roles():
    """
    Get trending job roles
    Query params:
    - country: country code (optional, default: 'in')
    """
    try:
        country = request.args.get('country', 'in')
        
        trending_roles = jobs_service.get_trending_roles(country)
        
        return jsonify({
            'country': country,
            'trendingRoles': trending_roles,
            'count': len(trending_roles)
        }), 200
        
    except Exception as e:
        logger.error(f"Get trending roles error: {str(e)}")
        return jsonify({
            'error': 'Failed to get trending roles',
            'code': 'GET_TRENDING_ERROR'
        }), 500

@jobs_bp.route('/countries', methods=['GET'])
def get_supported_countries():
    """Get list of supported countries for job search"""
    try:
        # Adzuna supported countries (subset)
        supported_countries = [
            {'code': 'in', 'name': 'India'},
            {'code': 'us', 'name': 'United States'},
            {'code': 'gb', 'name': 'United Kingdom'},
            {'code': 'ca', 'name': 'Canada'},
            {'code': 'au', 'name': 'Australia'},
            {'code': 'de', 'name': 'Germany'},
            {'code': 'fr', 'name': 'France'},
            {'code': 'nl', 'name': 'Netherlands'},
            {'code': 'sg', 'name': 'Singapore'},
            {'code': 'za', 'name': 'South Africa'}
        ]
        
        return jsonify({
            'countries': supported_countries
        }), 200
        
    except Exception as e:
        logger.error(f"Get supported countries error: {str(e)}")
        return jsonify({
            'error': 'Failed to get supported countries',
            'code': 'GET_COUNTRIES_ERROR'
        }), 500

@jobs_bp.route('/stats', methods=['GET'])
@optional_auth
def get_job_market_stats():
    """
    Get job market statistics
    Query params:
    - country: country code (optional, default: 'in')
    """
    try:
        country = request.args.get('country', 'in')
        
        # Get stats for popular tech roles
        popular_roles = [
            'Software Engineer',
            'Data Scientist',
            'Frontend Developer',
            'Backend Developer',
            'DevOps Engineer'
        ]
        
        role_stats = []
        total_jobs = 0
        
        for role in popular_roles:
            try:
                results = jobs_service.search_jobs(role, country, limit=1)
                job_count = results.get('total', 0)
                total_jobs += job_count
                
                role_stats.append({
                    'role': role,
                    'jobCount': job_count
                })
                
            except Exception as e:
                logger.warning(f"Error getting stats for {role}: {str(e)}")
                continue
        
        # Sort by job count
        role_stats.sort(key=lambda x: x['jobCount'], reverse=True)
        
        return jsonify({
            'country': country,
            'totalJobs': total_jobs,
            'roleStats': role_stats,
            'lastUpdated': 'real-time'
        }), 200
        
    except Exception as e:
        logger.error(f"Get job market stats error: {str(e)}")
        return jsonify({
            'error': 'Failed to get job market statistics',
            'code': 'GET_STATS_ERROR'
        }), 500