from flask import Blueprint, request, jsonify, current_app
from app.middleware.auth_required import auth_required
from app.db.firestore import FirestoreService
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import logging
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)
courses_bp = Blueprint('courses', __name__)
db_service = FirestoreService()

# YouTube API configuration
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

def get_youtube_service():
    """Initialize YouTube API service"""
    api_key = current_app.config.get('YOUTUBE_API_KEY')
    if not api_key:
        raise ValueError("YouTube API key not configured")
    
    return build(
        YOUTUBE_API_SERVICE_NAME, 
        YOUTUBE_API_VERSION, 
        developerKey=api_key
    )

def parse_duration(duration):
    """Parse YouTube duration format (PT4M13S) to seconds"""
    if not duration:
        return 0
    
    # Remove PT prefix
    duration = duration[2:]
    
    # Extract hours, minutes, seconds
    hours = 0
    minutes = 0
    seconds = 0
    
    if 'H' in duration:
        hours = int(duration.split('H')[0])
        duration = duration.split('H')[1]
    
    if 'M' in duration:
        minutes = int(duration.split('M')[0])
        duration = duration.split('M')[1]
    
    if 'S' in duration:
        seconds = int(duration.split('S')[0])
    
    return hours * 3600 + minutes * 60 + seconds

def format_duration(seconds):
    """Format seconds to human readable duration"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def clean_description(description, max_length=200):
    """Clean and truncate video description"""
    if not description:
        return ""
    
    # Remove URLs
    description = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', description)
    
    # Remove excessive whitespace
    description = re.sub(r'\s+', ' ', description).strip()
    
    # Truncate if too long
    if len(description) > max_length:
        description = description[:max_length] + "..."
    
    return description

@courses_bp.route('/search', methods=['GET'])
@auth_required
def search_courses():
    """
    Search for courses on YouTube based on skill or topic
    Query parameters:
    - q: Search query (required)
    - skill_level: beginner, intermediate, advanced (optional)
    - duration: short, medium, long (optional)
    - max_results: Number of results (default: 20, max: 50)
    - order: relevance, date, rating, viewCount, title (default: relevance)
    """
    try:
        # Get query parameters
        query = request.args.get('q')
        skill_level = request.args.get('skill_level', '')
        duration_filter = request.args.get('duration', '')
        max_results = min(int(request.args.get('max_results', 20)), 50)
        order = request.args.get('order', 'relevance')
        
        if not query:
            return jsonify({
                'error': 'Search query is required',
                'code': 'MISSING_QUERY'
            }), 400
        
        # Build search query with filters
        search_query = query
        if skill_level:
            search_query += f" {skill_level}"
        
        # Add common programming/learning keywords to improve results
        search_query += " tutorial course programming"
        
        youtube = get_youtube_service()
        
        # Search for videos
        search_request = youtube.search().list(
            q=search_query,
            part='id,snippet',
            maxResults=max_results,
            order=order,
            type='video',
            videoDuration=duration_filter if duration_filter in ['short', 'medium', 'long'] else None,
            videoDefinition='high',
            safeSearch='strict'
        )
        
        search_response = search_request.execute()
        
        if not search_response.get('items'):
            return jsonify({
                'courses': [],
                'total': 0,
                'query': query
            }), 200
        
        # Get video IDs for detailed information
        video_ids = [item['id']['videoId'] for item in search_response['items']]
        
        # Get video details (duration, statistics, etc.)
        videos_request = youtube.videos().list(
            part='contentDetails,statistics,snippet',
            id=','.join(video_ids)
        )
        
        videos_response = videos_request.execute()
        
        # Process and format results
        courses = []
        for video in videos_response['items']:
            try:
                snippet = video['snippet']
                content_details = video['contentDetails']
                statistics = video['statistics']
                
                # Parse duration
                duration_seconds = parse_duration(content_details.get('duration', ''))
                
                # Skip very short videos (less than 5 minutes) for courses
                if duration_seconds < 300:
                    continue
                
                course = {
                    'id': video['id'],
                    'title': snippet['title'],
                    'description': clean_description(snippet.get('description', '')),
                    'thumbnail': snippet['thumbnails'].get('high', {}).get('url', ''),
                    'channel': {
                        'name': snippet['channelTitle'],
                        'id': snippet['channelId']
                    },
                    'duration': {
                        'seconds': duration_seconds,
                        'formatted': format_duration(duration_seconds)
                    },
                    'statistics': {
                        'views': int(statistics.get('viewCount', 0)),
                        'likes': int(statistics.get('likeCount', 0)),
                        'comments': int(statistics.get('commentCount', 0))
                    },
                    'published_at': snippet['publishedAt'],
                    'url': f"https://www.youtube.com/watch?v={video['id']}",
                    'embed_url': f"https://www.youtube.com/embed/{video['id']}",
                    'skill_level': skill_level or 'intermediate',
                    'type': 'video'
                }
                
                courses.append(course)
                
            except Exception as e:
                logger.warning(f"Error processing video {video.get('id', 'unknown')}: {str(e)}")
                continue
        
        # Sort by view count and rating for better quality
        courses.sort(key=lambda x: (x['statistics']['views'], x['statistics']['likes']), reverse=True)
        
        return jsonify({
            'courses': courses,
            'total': len(courses),
            'query': query,
            'filters': {
                'skill_level': skill_level,
                'duration': duration_filter,
                'order': order
            }
        }), 200
        
    except HttpError as e:
        logger.error(f"YouTube API error: {str(e)}")
        return jsonify({
            'error': 'YouTube API error',
            'code': 'YOUTUBE_API_ERROR',
            'details': str(e)
        }), 500
        
    except Exception as e:
        logger.error(f"Search courses error: {str(e)}")
        return jsonify({
            'error': 'Failed to search courses',
            'code': 'SEARCH_ERROR'
        }), 500

@courses_bp.route('/recommendations', methods=['GET'])
@auth_required
def get_course_recommendations():
    """
    Get personalized course recommendations based on user's skills and target role
    """
    try:
        uid = request.current_user['uid']
        
        # Get user's skills and target role
        user_state = db_service.get_document('user_state', uid)
        
        if not user_state:
            return jsonify({
                'recommendations': [],
                'message': 'No user data found for recommendations'
            }), 200
        
        recommendations = []
        
        # Get recommendations based on missing skills from analysis
        if user_state.get('analysis') and user_state['analysis'].get('missingSkills'):
            missing_skills = user_state['analysis']['missingSkills'][:5]  # Top 5 missing skills
            
            youtube = get_youtube_service()
            
            for skill in missing_skills:
                try:
                    skill_name = skill.get('skillName', '')
                    if not skill_name:
                        continue
                    
                    # Search for courses for this skill
                    search_query = f"{skill_name} tutorial beginner course"
                    
                    search_request = youtube.search().list(
                        q=search_query,
                        part='id,snippet',
                        maxResults=3,
                        order='relevance',
                        type='video',
                        videoDuration='medium',
                        safeSearch='strict'
                    )
                    
                    search_response = search_request.execute()
                    
                    if search_response.get('items'):
                        # Get the best result
                        video = search_response['items'][0]
                        video_id = video['id']['videoId']
                        
                        # Get detailed video information
                        video_request = youtube.videos().list(
                            part='contentDetails,statistics,snippet',
                            id=video_id
                        )
                        
                        video_response = video_request.execute()
                        
                        if video_response['items']:
                            video_details = video_response['items'][0]
                            snippet = video_details['snippet']
                            content_details = video_details['contentDetails']
                            statistics = video_details['statistics']
                            
                            duration_seconds = parse_duration(content_details.get('duration', ''))
                            
                            # Only include videos longer than 10 minutes
                            if duration_seconds >= 600:
                                recommendation = {
                                    'id': video_id,
                                    'title': snippet['title'],
                                    'description': clean_description(snippet.get('description', '')),
                                    'thumbnail': snippet['thumbnails'].get('high', {}).get('url', ''),
                                    'channel': {
                                        'name': snippet['channelTitle'],
                                        'id': snippet['channelId']
                                    },
                                    'duration': {
                                        'seconds': duration_seconds,
                                        'formatted': format_duration(duration_seconds)
                                    },
                                    'statistics': {
                                        'views': int(statistics.get('viewCount', 0)),
                                        'likes': int(statistics.get('likeCount', 0))
                                    },
                                    'url': f"https://www.youtube.com/watch?v={video_id}",
                                    'embed_url': f"https://www.youtube.com/embed/{video_id}",
                                    'skill': skill_name,
                                    'reason': f"Recommended for learning {skill_name}",
                                    'priority': 'high' if skill.get('required') == 'advanced' else 'medium'
                                }
                                
                                recommendations.append(recommendation)
                
                except Exception as e:
                    logger.warning(f"Error getting recommendation for skill {skill.get('skillName', 'unknown')}: {str(e)}")
                    continue
        
        # If no specific recommendations, get general programming courses
        if not recommendations:
            try:
                youtube = get_youtube_service()
                
                general_queries = [
                    "programming fundamentals course",
                    "web development tutorial",
                    "data structures algorithms",
                    "software engineering basics"
                ]
                
                for query in general_queries[:2]:  # Limit to 2 general recommendations
                    search_request = youtube.search().list(
                        q=query,
                        part='id,snippet',
                        maxResults=1,
                        order='relevance',
                        type='video',
                        videoDuration='long',
                        safeSearch='strict'
                    )
                    
                    search_response = search_request.execute()
                    
                    if search_response.get('items'):
                        video = search_response['items'][0]
                        video_id = video['id']['videoId']
                        
                        recommendation = {
                            'id': video_id,
                            'title': video['snippet']['title'],
                            'description': clean_description(video['snippet'].get('description', '')),
                            'thumbnail': video['snippet']['thumbnails'].get('high', {}).get('url', ''),
                            'channel': {
                                'name': video['snippet']['channelTitle'],
                                'id': video['snippet']['channelId']
                            },
                            'url': f"https://www.youtube.com/watch?v={video_id}",
                            'embed_url': f"https://www.youtube.com/embed/{video_id}",
                            'reason': "General programming course recommendation",
                            'priority': 'low'
                        }
                        
                        recommendations.append(recommendation)
            
            except Exception as e:
                logger.warning(f"Error getting general recommendations: {str(e)}")
        
        return jsonify({
            'recommendations': recommendations,
            'total': len(recommendations)
        }), 200
        
    except Exception as e:
        logger.error(f"Get recommendations error: {str(e)}")
        return jsonify({
            'error': 'Failed to get course recommendations',
            'code': 'RECOMMENDATIONS_ERROR'
        }), 500

@courses_bp.route('/save', methods=['POST'])
@auth_required
def save_course():
    """
    Save a course to user's saved courses list
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        if not data or not data.get('course_id'):
            return jsonify({
                'error': 'Course ID is required',
                'code': 'MISSING_COURSE_ID'
            }), 400
        
        course_data = {
            'course_id': data['course_id'],
            'title': data.get('title', ''),
            'url': data.get('url', ''),
            'thumbnail': data.get('thumbnail', ''),
            'channel': data.get('channel', {}),
            'duration': data.get('duration', {}),
            'skill': data.get('skill', ''),
            'saved_at': datetime.utcnow(),
            'completed': False,
            'progress': 0
        }
        
        # Save to user's saved courses
        saved_courses = db_service.get_document('saved_courses', uid) or {'courses': []}
        
        # Check if already saved
        existing_course = next((c for c in saved_courses['courses'] if c['course_id'] == data['course_id']), None)
        
        if existing_course:
            return jsonify({
                'message': 'Course already saved',
                'course': existing_course
            }), 200
        
        saved_courses['courses'].append(course_data)
        saved_courses['updated_at'] = datetime.utcnow()
        
        success = db_service.create_document('saved_courses', uid, saved_courses)
        
        if not success:
            return jsonify({
                'error': 'Failed to save course',
                'code': 'SAVE_FAILED'
            }), 500
        
        # Log activity
        db_service.log_user_activity(uid, 'COURSE_SAVED', f'Saved course: {course_data["title"]}')
        
        return jsonify({
            'message': 'Course saved successfully',
            'course': course_data
        }), 200
        
    except Exception as e:
        logger.error(f"Save course error: {str(e)}")
        return jsonify({
            'error': 'Failed to save course',
            'code': 'SAVE_COURSE_ERROR'
        }), 500

@courses_bp.route('/saved', methods=['GET'])
@auth_required
def get_saved_courses():
    """
    Get user's saved courses
    """
    try:
        uid = request.current_user['uid']
        
        saved_courses = db_service.get_document('saved_courses', uid)
        
        if not saved_courses:
            return jsonify({
                'courses': [],
                'total': 0
            }), 200
        
        courses = saved_courses.get('courses', [])
        
        # Sort by saved date (most recent first)
        courses.sort(key=lambda x: x.get('saved_at', datetime.min), reverse=True)
        
        return jsonify({
            'courses': courses,
            'total': len(courses)
        }), 200
        
    except Exception as e:
        logger.error(f"Get saved courses error: {str(e)}")
        return jsonify({
            'error': 'Failed to get saved courses',
            'code': 'GET_SAVED_COURSES_ERROR'
        }), 500

@courses_bp.route('/progress', methods=['PUT'])
@auth_required
def update_course_progress():
    """
    Update progress for a saved course
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()
        
        if not data or not data.get('course_id'):
            return jsonify({
                'error': 'Course ID is required',
                'code': 'MISSING_COURSE_ID'
            }), 400
        
        course_id = data['course_id']
        progress = min(max(int(data.get('progress', 0)), 0), 100)  # Clamp between 0-100
        completed = data.get('completed', progress >= 100)
        
        # Get saved courses
        saved_courses = db_service.get_document('saved_courses', uid)
        
        if not saved_courses or not saved_courses.get('courses'):
            return jsonify({
                'error': 'Course not found in saved courses',
                'code': 'COURSE_NOT_FOUND'
            }), 404
        
        # Find and update the course
        course_updated = False
        for course in saved_courses['courses']:
            if course['course_id'] == course_id:
                course['progress'] = progress
                course['completed'] = completed
                course['last_watched'] = datetime.utcnow()
                course_updated = True
                break
        
        if not course_updated:
            return jsonify({
                'error': 'Course not found in saved courses',
                'code': 'COURSE_NOT_FOUND'
            }), 404
        
        saved_courses['updated_at'] = datetime.utcnow()
        
        success = db_service.update_document('saved_courses', uid, saved_courses)
        
        if not success:
            return jsonify({
                'error': 'Failed to update course progress',
                'code': 'UPDATE_FAILED'
            }), 500
        
        # Log activity
        activity_message = f'Completed course: {course["title"]}' if completed else f'Updated progress for: {course["title"]} ({progress}%)'
        db_service.log_user_activity(uid, 'COURSE_PROGRESS_UPDATED', activity_message)
        
        return jsonify({
            'message': 'Course progress updated successfully',
            'progress': progress,
            'completed': completed
        }), 200
        
    except Exception as e:
        logger.error(f"Update course progress error: {str(e)}")
        return jsonify({
            'error': 'Failed to update course progress',
            'code': 'UPDATE_PROGRESS_ERROR'
        }), 500

@courses_bp.route('/remove', methods=['DELETE'])
@auth_required
def remove_saved_course():
    """
    Remove a course from saved courses
    """
    try:
        uid = request.current_user['uid']
        course_id = request.args.get('course_id')
        
        if not course_id:
            return jsonify({
                'error': 'Course ID is required',
                'code': 'MISSING_COURSE_ID'
            }), 400
        
        # Get saved courses
        saved_courses = db_service.get_document('saved_courses', uid)
        
        if not saved_courses or not saved_courses.get('courses'):
            return jsonify({
                'error': 'No saved courses found',
                'code': 'NO_SAVED_COURSES'
            }), 404
        
        # Remove the course
        original_count = len(saved_courses['courses'])
        saved_courses['courses'] = [c for c in saved_courses['courses'] if c['course_id'] != course_id]
        
        if len(saved_courses['courses']) == original_count:
            return jsonify({
                'error': 'Course not found in saved courses',
                'code': 'COURSE_NOT_FOUND'
            }), 404
        
        saved_courses['updated_at'] = datetime.utcnow()
        
        success = db_service.update_document('saved_courses', uid, saved_courses)
        
        if not success:
            return jsonify({
                'error': 'Failed to remove course',
                'code': 'REMOVE_FAILED'
            }), 500
        
        # Log activity
        db_service.log_user_activity(uid, 'COURSE_REMOVED', f'Removed saved course: {course_id}')
        
        return jsonify({
            'message': 'Course removed successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Remove saved course error: {str(e)}")
        return jsonify({
            'error': 'Failed to remove course',
            'code': 'REMOVE_COURSE_ERROR'
        }), 500