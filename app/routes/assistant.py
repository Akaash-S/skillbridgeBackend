"""
Assistant Routes for SkillBridge Learning Assistant

Provides API endpoints for the AI chatbot:
- POST /assistant/chat — Send a message and get AI response (supports SSE streaming)
- GET  /assistant/history — Get chat history for the current session
- DELETE /assistant/history — Clear chat history
- GET  /assistant/prompts — Get suggested prompts based on current context
"""

import json
import logging
from flask import Blueprint, request, jsonify, Response, stream_with_context
from app.middleware.auth_required import auth_required
from app.services.learning_assistant_service import LearningAssistantService
from app.utils.validators import validate_required_fields
from app import limiter

logger = logging.getLogger(__name__)
assistant_bp = Blueprint('assistant', __name__)

assistant_service = LearningAssistantService()


@assistant_bp.route('/chat', methods=['POST'])
@auth_required
@limiter.limit("30 per minute")
def chat():
    """
    Send a message to the AI Learning Assistant.

    Request body:
    {
        "message": "Explain Docker volumes",
        "context": {
            "role": "DevOps Engineer",
            "module": "Docker",
            "learningMode": "documentation",
            "currentSection": "Container Storage",
            "roadmapProgress": 45,
            "moduleIndex": 2
        },
        "sessionId": "optional-session-id",
        "stream": true  (optional, defaults to true)
    }

    Response (streaming): Server-Sent Events
    Response (non-streaming): { "response": "...", "sessionId": "..." }
    """
    try:
        uid = request.current_user['uid']
        data = request.get_json()

        if not data or not data.get('message', '').strip():
            return jsonify({
                'error': 'Message is required',
                'code': 'VALIDATION_ERROR',
            }), 400

        message = data['message'].strip()
        context = data.get('context', {})
        session_id = data.get('sessionId')
        use_stream = data.get('stream', True)

        # Check if service is available
        if not assistant_service.is_available():
            return jsonify({
                'error': 'AI Learning Assistant is currently unavailable',
                'code': 'SERVICE_UNAVAILABLE',
            }), 503

        if use_stream:
            # Streaming response via Server-Sent Events
            result = assistant_service.process_message(
                uid=uid,
                message=message,
                context=context,
                session_id=session_id,
                stream=True,
            )

            if result.get('error'):
                return jsonify({
                    'error': result.get('response', 'An error occurred'),
                    'code': 'ASSISTANT_ERROR',
                }), 500

            if result.get('rateLimited'):
                return jsonify({
                    'error': result.get('response', 'Rate limited'),
                    'code': 'RATE_LIMITED',
                    'sessionId': result.get('sessionId', ''),
                }), 429

            returned_session_id = result.get('sessionId', '')
            stream_generator = result.get('stream')

            def generate():
                """Generate SSE events from the stream"""
                full_response = []
                try:
                    # Send session ID as first event
                    yield f"data: {json.dumps({'sessionId': returned_session_id, 'chunk': '', 'done': False})}\n\n"

                    for chunk in stream_generator:
                        full_response.append(chunk)
                        yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"

                    # Send completion event
                    yield f"data: {json.dumps({'chunk': '', 'done': True})}\n\n"

                    # Store the complete response
                    complete_text = ''.join(full_response)
                    if complete_text:
                        assistant_service.store_assistant_response(
                            uid, returned_session_id, complete_text
                        )

                except Exception as e:
                    logger.error(f"❌ Streaming error: {str(e)}")
                    yield f"data: {json.dumps({'chunk': 'An error occurred during streaming.', 'done': True, 'error': True})}\n\n"

            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',  # Disable nginx buffering
                    'Connection': 'keep-alive',
                },
            )
        else:
            # Non-streaming response
            result = assistant_service.process_message(
                uid=uid,
                message=message,
                context=context,
                session_id=session_id,
                stream=False,
            )

            if result.get('error'):
                return jsonify({
                    'error': result.get('response', 'An error occurred'),
                    'code': 'ASSISTANT_ERROR',
                }), 500

            if result.get('rateLimited'):
                return jsonify({
                    'error': result.get('response', 'Rate limited'),
                    'code': 'RATE_LIMITED',
                    'sessionId': result.get('sessionId', ''),
                }), 429

            return jsonify({
                'response': result.get('response', ''),
                'sessionId': result.get('sessionId', ''),
            }), 200

    except Exception as e:
        logger.error(f"❌ Chat endpoint error: {str(e)}")
        return jsonify({
            'error': 'Failed to process message',
            'code': 'CHAT_ERROR',
        }), 500


@assistant_bp.route('/history', methods=['GET'])
@auth_required
def get_history():
    """
    Get chat history for the current user.

    Query params:
        sessionId (optional) — specific session to retrieve
    """
    try:
        uid = request.current_user['uid']
        session_id = request.args.get('sessionId')

        history = assistant_service.get_chat_history(uid, session_id)

        return jsonify(history), 200

    except Exception as e:
        logger.error(f"❌ Get history error: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve chat history',
            'code': 'HISTORY_ERROR',
        }), 500


@assistant_bp.route('/history', methods=['DELETE'])
@auth_required
def clear_history():
    """
    Clear chat history for the current user.

    Query params:
        sessionId (optional) — specific session to clear
    """
    try:
        uid = request.current_user['uid']
        session_id = request.args.get('sessionId')

        success = assistant_service.clear_chat_history(uid, session_id)

        if success:
            return jsonify({
                'message': 'Chat history cleared successfully',
            }), 200
        else:
            return jsonify({
                'error': 'Failed to clear chat history',
                'code': 'CLEAR_HISTORY_ERROR',
            }), 500

    except Exception as e:
        logger.error(f"❌ Clear history error: {str(e)}")
        return jsonify({
            'error': 'Failed to clear chat history',
            'code': 'CLEAR_HISTORY_ERROR',
        }), 500


@assistant_bp.route('/prompts', methods=['GET'])
@auth_required
def get_prompts():
    """
    Get suggested prompts based on the user's current learning context.

    Query params:
        role — current target role
        module — current module name
        currentSection — current section within the module
    """
    try:
        context = {
            'role': request.args.get('role', ''),
            'module': request.args.get('module', ''),
            'currentSection': request.args.get('currentSection', ''),
        }

        prompts = assistant_service.get_suggested_prompts(context)

        return jsonify({
            'prompts': prompts,
        }), 200

    except Exception as e:
        logger.error(f"❌ Get prompts error: {str(e)}")
        return jsonify({
            'error': 'Failed to get suggested prompts',
            'code': 'PROMPTS_ERROR',
        }), 500
