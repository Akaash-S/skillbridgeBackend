from app.db.firestore import FirestoreService
from typing import Dict, List, Optional
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

OFFICIAL_DOCS_MAPPING = {
    'html': [
        {'title': 'MDN Web Docs: HTML', 'url': 'https://developer.mozilla.org/en-US/docs/Web/HTML', 'provider': 'Mozilla MDN'},
        {'title': 'HTML Living Standard', 'url': 'https://html.spec.whatwg.org/', 'provider': 'WHATWG'}
    ],
    'css': [
        {'title': 'MDN Web Docs: CSS', 'url': 'https://developer.mozilla.org/en-US/docs/Web/CSS', 'provider': 'Mozilla MDN'},
        {'title': 'W3C CSS Home', 'url': 'https://www.w3.org/Style/CSS/', 'provider': 'W3C'}
    ],
    'javascript': [
        {'title': 'MDN Web Docs: JavaScript Guide', 'url': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide', 'provider': 'Mozilla MDN'},
        {'title': 'Modern JavaScript Tutorial', 'url': 'https://javascript.info/', 'provider': 'Javascript.info'}
    ],
    'typescript': [
        {'title': 'TypeScript Documentation', 'url': 'https://www.typescriptlang.org/docs/', 'provider': 'Microsoft'},
        {'title': 'TypeScript Deep Dive', 'url': 'https://basarat.gitbook.io/typescript/', 'provider': 'Basarat Ali'}
    ],
    'react': [
        {'title': 'React Documentation & Reference', 'url': 'https://react.dev/reference/react', 'provider': 'Meta'},
        {'title': 'React Dev Guides', 'url': 'https://react.dev/learn', 'provider': 'Meta'}
    ],
    'python': [
        {'title': 'Python 3 Documentation', 'url': 'https://docs.python.org/3/', 'provider': 'Python Software Foundation'},
        {'title': 'The Hitchhiker\'s Guide to Python', 'url': 'https://docs.python-guide.org/', 'provider': 'Kenneth Reitz'}
    ],
    'sql': [
        {'title': 'W3Schools SQL Tutorial', 'url': 'https://www.w3schools.com/sql/', 'provider': 'W3Schools'},
        {'title': 'PostgreSQL Documentation', 'url': 'https://www.postgresql.org/docs/', 'provider': 'PostgreSQL'}
    ],
    'docker': [
        {'title': 'Docker Documentation Home', 'url': 'https://docs.docker.com/', 'provider': 'Docker Inc.'},
        {'title': 'Docker Get Started Guide', 'url': 'https://docs.docker.com/get-started/', 'provider': 'Docker Inc.'}
    ],
    'kubernetes': [
        {'title': 'Kubernetes Documentation', 'url': 'https://kubernetes.io/docs/home/', 'provider': 'CNCF'},
        {'title': 'Kubernetes Tutorials', 'url': 'https://kubernetes.io/docs/tutorials/', 'provider': 'CNCF'}
    ],
    'aws': [
        {'title': 'AWS Documentation Center', 'url': 'https://docs.aws.amazon.com/', 'provider': 'Amazon Web Services'},
        {'title': 'AWS Getting Started Guides', 'url': 'https://aws.amazon.com/getting-started/', 'provider': 'Amazon Web Services'}
    ],
    'git': [
        {'title': 'Git Reference Manual', 'url': 'https://git-scm.com/doc', 'provider': 'Git Core'},
        {'title': 'Pro Git Book', 'url': 'https://git-scm.com/book/en/v2', 'provider': 'Scott Chacon & Ben Straub'}
    ]
}

class LearningService:
    """Learning resources and progress tracking service"""
    
    def __init__(self):
        self.db_service = FirestoreService()
    
    def get_learning_resources(self, skill_id: str, level: str = None, resource_type: str = None, role_title: str = None, role_id: str = None) -> List[Dict]:
        """Get learning resources for a specific skill, prioritizing/fetching role-specific ones"""
        try:
            filters = [('skillId', '==', skill_id)]
            
            if level:
                filters.append(('level', '==', level))
            
            if resource_type:
                filters.append(('type', '==', resource_type))
            
            resources = self.db_service.query_collection('learning_resources', filters)
            
            # Check if we have video resources for this skill matching the role. If not, fetch from YouTube API and cache them.
            role_videos = [r for r in resources if r.get('type') == 'video' and r.get('roleId') == role_id]
            if len(role_videos) < 2 and (not resource_type or resource_type == 'video') and role_title:
                friendly_name = skill_id.replace('-', ' ').replace('_', ' ').title()
                yt_videos = self.fetch_and_cache_youtube_videos(skill_id, friendly_name, role_title, role_id)
                if yt_videos:
                    resources.extend(yt_videos)
                    
            # Check if we have documentation resources for this skill matching the role. If not, generate and cache them.
            role_docs = [r for r in resources if r.get('type') in ['documentation', 'book', 'article'] and r.get('roleId') == role_id]
            if len(role_docs) < 2 and (not resource_type or resource_type != 'video') and role_title:
                new_docs = self.generate_and_cache_documentation_resources(skill_id, role_title, role_id)
                if new_docs:
                    resources.extend(new_docs)
            
            # Prioritize matching roleId first, then by rating/verified status
            resources.sort(key=lambda x: (
                x.get('roleId') == role_id if role_id else False,
                x.get('verified', False),
                x.get('rating', 0)
            ), reverse=True)
            
            return resources
            
        except Exception as e:
            logger.error(f"Error getting learning resources: {str(e)}")
            return []

    def fetch_and_cache_youtube_videos(self, skill_id: str, skill_name: str, role_title: str = None, role_id: str = None) -> List[Dict]:
        """Fetch videos from YouTube API for a skill and cache them in Firestore with role context"""
        api_key = os.environ.get('YOUTUBE_API_KEY')
        if not api_key:
            logger.warning("YOUTUBE_API_KEY not found in environment. Skipping YouTube fetch.")
            return []
            
        try:
            from googleapiclient.discovery import build
            
            youtube = build('youtube', 'v3', developerKey=api_key)
            
            # Search query including the target role context if available
            if role_title:
                query = f"{skill_name} for {role_title} tutorial beginner course"
            else:
                query = f"{skill_name} tutorial beginner course"
            
            logger.info(f"Fetching fresh YouTube videos for query: {query}")
            search_request = youtube.search().list(
                q=query,
                part='id,snippet',
                maxResults=3,
                order='relevance',
                type='video',
                safeSearch='strict'
            )
            
            search_response = search_request.execute()
            items = search_response.get('items', [])
            
            new_resources = []
            for item in items:
                video_id = item['id'].get('videoId')
                if not video_id:
                    continue
                    
                snippet = item.get('snippet', {})
                title = snippet.get('title', 'YouTube Tutorial')
                channel_title = snippet.get('channelTitle', 'YouTube')
                
                # Make the ID unique to the role so we cache separate links per role
                resource_id = f"yt_{role_id}_{video_id}" if role_id else f"yt_{video_id}"
                
                video_resource = {
                    'id': resource_id,
                    'skillId': skill_id,
                    'roleId': role_id,
                    'roleTitle': role_title,
                    'title': title,
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'type': 'video',
                    'duration': '20m', # Default duration approximation
                    'provider': channel_title,
                    'rating': 4.7,
                    'verified': True,
                    'level': 'beginner'
                }
                
                # Cache to firestore
                self.db_service.create_document('learning_resources', resource_id, video_resource)
                new_resources.append(video_resource)
                
            return new_resources
            
        except Exception as e:
            logger.error(f"Error fetching/caching YouTube videos for {skill_id}: {str(e)}")
            return []

    def generate_and_cache_documentation_resources(self, skill_id: str, role_title: str = None, role_id: str = None) -> List[Dict]:
        """Generate official/fallback documentation resources for a skill and cache them in Firestore with role context"""
        try:
            # Look up in mapping
            mapped_docs = OFFICIAL_DOCS_MAPPING.get(skill_id.lower())
            
            friendly_name = skill_id.replace('-', ' ').replace('_', ' ').title()
            
            # If we have role context, create a customized doc entry to add to it
            role_custom_docs = []
            if role_title:
                role_custom_docs = [
                    {
                        'title': f'{friendly_name} Guide for {role_title}',
                        'url': f'https://www.google.com/search?q={friendly_name}+for+{role_title.replace(" ", "+")}+official+documentation',
                        'provider': f'{role_title} Reference'
                    }
                ]
            
            if not mapped_docs:
                # Fallback generator for unknown skill
                mapped_docs = [
                    {
                        'title': f'{friendly_name} Developer Documentation',
                        'url': f'https://devdocs.io/{skill_id.lower()}/',
                        'provider': 'DevDocs'
                    }
                ]
                
            # Combine role-specific docs first, then general official docs
            all_docs = role_custom_docs + mapped_docs
                
            new_resources = []
            for i, doc in enumerate(all_docs):
                resource_id = f"doc_{role_id}_{skill_id}_{i+1}" if role_id else f"doc_{skill_id}_{i+1}"
                
                doc_resource = {
                    'id': resource_id,
                    'skillId': skill_id,
                    'roleId': role_id,
                    'roleTitle': role_title,
                    'title': doc['title'],
                    'url': doc['url'],
                    'type': 'documentation',
                    'duration': 'Self-paced',
                    'provider': doc['provider'],
                    'rating': 4.8,
                    'verified': True,
                    'level': 'intermediate'
                }
                
                # Cache to firestore
                self.db_service.create_document('learning_resources', resource_id, doc_resource)
                new_resources.append(doc_resource)
                
            return new_resources
            
        except Exception as e:
            logger.error(f"Error generating/caching documentation for {skill_id}: {str(e)}")
            return []
    
    def search_learning_resources(self, query: str, limit: int = 20) -> List[Dict]:
        """Search learning resources by title or provider"""
        try:
            # Get all resources (Firestore doesn't support full-text search natively)
            all_resources = self.db_service.query_collection('learning_resources')
            
            query_lower = query.lower()
            matching_resources = []
            
            for resource in all_resources:
                # Check title
                if query_lower in resource.get('title', '').lower():
                    matching_resources.append(resource)
                    continue
                
                # Check provider
                if query_lower in resource.get('provider', '').lower():
                    matching_resources.append(resource)
                    continue
                
                # Check skill name (if available)
                skill_name = resource.get('skillName', '')
                if query_lower in skill_name.lower():
                    matching_resources.append(resource)
            
            # Sort by relevance (verified first, then by rating)
            matching_resources.sort(key=lambda x: (x.get('verified', False), x.get('rating', 0)), reverse=True)
            
            return matching_resources[:limit]
            
        except Exception as e:
            logger.error(f"Error searching learning resources: {str(e)}")
            return []
    
    def get_resources_by_category(self, category: str, limit: int = 50) -> List[Dict]:
        """Get learning resources by skill category"""
        try:
            # First get skills in the category
            skills_in_category = self.db_service.query_collection(
                'skills_master', 
                [('category', '==', category)]
            )
            
            skill_ids = [skill['skillId'] for skill in skills_in_category]
            
            # Get resources for these skills
            all_resources = []
            for skill_id in skill_ids:
                resources = self.get_learning_resources(skill_id)
                all_resources.extend(resources)
            
            # Remove duplicates and sort
            unique_resources = []
            seen_urls = set()
            
            for resource in all_resources:
                url = resource.get('url', '')
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_resources.append(resource)
            
            # Sort by rating and verified status
            unique_resources.sort(key=lambda x: (x.get('verified', False), x.get('rating', 0)), reverse=True)
            
            return unique_resources[:limit]
            
        except Exception as e:
            logger.error(f"Error getting resources by category: {str(e)}")
            return []
    
    def mark_resource_completed(self, uid: str, resource_id: str, skill_id: str) -> bool:
        """Mark a learning resource as completed by user"""
        try:
            completion_data = {
                'uid': uid,
                'resourceId': resource_id,
                'skillId': skill_id,
                'completedAt': datetime.utcnow(),
                'source': 'user-reported'
            }
            
            # Create unique ID for completion record
            completion_id = f"{uid}_{resource_id}"
            
            success = self.db_service.create_document('learning_completions', completion_id, completion_data)
            
            if success:
                # Get resource details for logging
                resource = self.db_service.get_document('learning_resources', resource_id)
                resource_title = resource.get('title', 'Unknown Resource') if resource else 'Unknown Resource'
                
                # Log activity
                self.db_service.log_user_activity(
                    uid,
                    'LEARNING_COMPLETED',
                    f'Completed: {resource_title}'
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error marking resource completed: {str(e)}")
            return False
    
    def get_user_completions(self, uid: str, skill_id: str = None) -> List[Dict]:
        """Get user's completed learning resources"""
        try:
            filters = [('uid', '==', uid)]
            
            if skill_id:
                filters.append(('skillId', '==', skill_id))
            
            completions = self.db_service.query_collection('learning_completions', filters)
            
            # Enrich with resource details
            enriched_completions = []
            for completion in completions:
                resource_id = completion.get('resourceId')
                resource = self.db_service.get_document('learning_resources', resource_id)
                
                if resource:
                    enriched_completion = {
                        **completion,
                        'resource': resource
                    }
                    enriched_completions.append(enriched_completion)
            
            # Sort by completion date (most recent first)
            enriched_completions.sort(key=lambda x: x.get('completedAt', datetime.min), reverse=True)
            
            return enriched_completions
            
        except Exception as e:
            logger.error(f"Error getting user completions: {str(e)}")
            return []
    
    def get_learning_stats(self, uid: str) -> Dict:
        """Get user's learning statistics"""
        try:
            # Get all completions
            completions = self.get_user_completions(uid)
            
            # Calculate stats
            total_completed = len(completions)
            
            # Group by skill
            skills_learned = {}
            for completion in completions:
                skill_id = completion.get('skillId')
                if skill_id:
                    if skill_id not in skills_learned:
                        skills_learned[skill_id] = 0
                    skills_learned[skill_id] += 1
            
            # Group by resource type
            types_completed = {}
            for completion in completions:
                resource = completion.get('resource', {})
                resource_type = resource.get('type', 'unknown')
                if resource_type not in types_completed:
                    types_completed[resource_type] = 0
                types_completed[resource_type] += 1
            
            # Calculate total learning hours (estimated)
            total_hours = 0
            for completion in completions:
                resource = completion.get('resource', {})
                duration_str = resource.get('duration', '0h')
                
                # Simple parsing of duration (e.g., "2h", "30m", "1.5h")
                try:
                    if 'h' in duration_str:
                        hours = float(duration_str.replace('h', '').strip())
                        total_hours += hours
                    elif 'm' in duration_str:
                        minutes = float(duration_str.replace('m', '').strip())
                        total_hours += minutes / 60
                except:
                    pass  # Skip invalid duration formats
            
            return {
                'totalCompleted': total_completed,
                'uniqueSkills': len(skills_learned),
                'skillsBreakdown': skills_learned,
                'typesBreakdown': types_completed,
                'estimatedHours': round(total_hours, 1)
            }
            
        except Exception as e:
            logger.error(f"Error getting learning stats: {str(e)}")
            return {
                'totalCompleted': 0,
                'uniqueSkills': 0,
                'skillsBreakdown': {},
                'typesBreakdown': {},
                'estimatedHours': 0
            }
    
    def get_recommended_resources(self, uid: str, limit: int = 10) -> List[Dict]:
        """Get recommended learning resources based on user's skills and roadmap"""
        try:
            # Get user's current skills
            user_skills = self.db_service.get_user_skills(uid)
            user_skill_ids = {skill['skillId'] for skill in user_skills}
            
            # Get user's active roadmap
            roadmap = self.db_service.get_user_roadmap(uid)
            
            recommended_resources = []
            
            if roadmap:
                # Get resources for roadmap skills
                milestones = roadmap.get('milestones', [])
                
                for milestone in milestones:
                    if milestone.get('completed', False):
                        continue  # Skip completed milestones
                    
                    skills = milestone.get('skills', [])
                    for skill in skills:
                        if skill.get('completed', False):
                            continue  # Skip completed skills
                        
                        skill_id = skill.get('skillId')
                        target_level = skill.get('targetLevel', 'intermediate')
                        
                        # Get resources for this skill
                        resources = self.get_learning_resources(skill_id, target_level)
                        
                        # Add roadmap context to resources
                        for resource in resources[:2]:  # Limit per skill
                            resource_with_context = {
                                **resource,
                                'recommendationReason': f'Part of your {roadmap.get("roleId", "career")} roadmap',
                                'priority': skill.get('priority', 'medium'),
                                'milestoneTitle': milestone.get('title', 'Learning Milestone')
                            }
                            recommended_resources.append(resource_with_context)
            
            # If no roadmap or need more recommendations, suggest based on current skills
            if len(recommended_resources) < limit:
                for skill in user_skills:
                    skill_id = skill['skillId']
                    current_level = skill['level']
                    
                    # Suggest next level resources
                    next_level = self._get_next_level(current_level)
                    if next_level:
                        resources = self.get_learning_resources(skill_id, next_level)
                        
                        for resource in resources[:1]:  # One per skill
                            resource_with_context = {
                                **resource,
                                'recommendationReason': f'Advance your {skill_id} skills to {next_level}',
                                'priority': 'medium'
                            }
                            recommended_resources.append(resource_with_context)
                            
                            if len(recommended_resources) >= limit:
                                break
                    
                    if len(recommended_resources) >= limit:
                        break
            
            # Remove duplicates and limit results
            unique_resources = []
            seen_urls = set()
            
            for resource in recommended_resources:
                url = resource.get('url', '')
                if url not in seen_urls and len(unique_resources) < limit:
                    seen_urls.add(url)
                    unique_resources.append(resource)
            
            return unique_resources
            
        except Exception as e:
            logger.error(f"Error getting recommended resources: {str(e)}")
            return []
    
    def _get_next_level(self, current_level: str) -> Optional[str]:
        """Get the next proficiency level"""
        level_progression = {
            'beginner': 'intermediate',
            'intermediate': 'advanced',
            'advanced': None  # No next level
        }
        return level_progression.get(current_level)

    def set_learning_mode(self, uid: str, learning_mode: str) -> bool:
        """Set user's learning preference mode"""
        try:
            # Save to users collection
            success = self.db_service.update_document('users', uid, {'learningMode': learning_mode}, create_if_missing=True)
            if success:
                # Also sync to user_state collection to easily load on initial load
                self.db_service.update_document('user_state', uid, {'learningMode': learning_mode}, create_if_missing=True)
                logger.info(f"Successfully set learning mode '{learning_mode}' for user {uid}")
            return success
        except Exception as e:
            logger.error(f"Error setting learning mode: {str(e)}")
            return False