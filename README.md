# SkillBridge Suite - REST Backend

A production-ready REST API backend for the SkillBridge Suite career development platform, built with Flask, Firebase, Firestore, and Gemini AI.

## 🚀 Features

- **Firebase Google Authentication** - Secure user authentication with Google OAuth
- **AI-Powered Roadmaps** - Personalized learning paths generated using Gemini 2.0 Flash
- **Skills Management** - Comprehensive skill tracking and gap analysis
- **Job Matching** - Real-time job search using Adzuna API
- **Learning Resources** - Curated learning materials with progress tracking
- **Activity Logging** - Complete user activity and progress tracking
- **Email Notifications** - SMTP-based email system for user engagement
- **Production Ready** - Docker deployment with Nginx, SSL, and security best practices

## 🛠️ Tech Stack

- **Language**: Python 3.11
- **Framework**: Flask 3.0
- **Authentication**: Firebase Admin SDK
- **Database**: Google Firestore (Native mode)
- **AI**: Google Gemini 2.0 Flash
- **Jobs API**: Adzuna
- **Email**: SMTP (Gmail/SendGrid)
- **Deployment**: Docker + Nginx + Certbot
- **Server**: Google Cloud VM

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── main.py                  # Application entry point
│   ├── config.py                # Configuration management
│   │
│   ├── routes/                  # API route handlers
│   │   ├── auth.py             # Authentication endpoints
│   │   ├── users.py            # User profile management
│   │   ├── skills.py           # Skills CRUD operations
│   │   ├── roadmap.py          # AI roadmap generation
│   │   ├── learning.py         # Learning resources
│   │   ├── jobs.py             # Job search and matching
│   │   ├── activity.py         # Activity logging
│   │   └── settings.py         # User settings
│   │
│   ├── services/               # Business logic services
│   │   ├── firebase_service.py # Firebase authentication
│   │   ├── skills_engine.py    # Skills management engine
│   │   ├── roadmap_ai.py       # AI roadmap generation
│   │   ├── jobs_service.py     # Job search service
│   │   ├── learning_service.py # Learning resources
│   │   └── email_service.py    # Email notifications
│   │
│   ├── middleware/             # Custom middleware
│   │   └── auth_required.py    # Authentication decorators
│   │
│   ├── db/                     # Database layer
│   │   └── firestore.py        # Firestore operations
│   │
│   └── utils/                  # Utility functions
│       ├── validators.py       # Input validation
│       └── helpers.py          # Helper functions
│
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Multi-container setup
├── nginx.conf                  # Nginx configuration
├── .env.example               # Environment variables template
└── README.md                  # This file
```

## 🔧 Installation & Setup

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Firebase project with Firestore
- Google Cloud project with Gemini API access
- Adzuna API credentials
- SMTP email credentials

### 1. Clone Repository

```bash
git clone <repository-url>
cd backend
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:

```env
# Flask
SECRET_KEY=your-secret-key-change-in-production
FLASK_ENV=production

# Firebase
GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase-service-account.json

# Gemini AI
GEMINI_API_KEY=your-gemini-api-key

# Adzuna Jobs API
ADZUNA_APP_ID=your-adzuna-app-id
ADZUNA_APP_KEY=your-adzuna-app-key

# SMTP Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 3. Firebase Setup

1. Create a Firebase project at https://console.firebase.google.com
2. Enable Authentication with Google provider
3. Create a Firestore database in Native mode
4. Generate a service account key and save as `credentials/firebase-service-account.json`

### 4. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app/main.py
```

The API will be available at `http://localhost:8000`

### 5. Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🔒 Security Features

- **Firebase Authentication** - Industry-standard OAuth with Google
- **Input Validation** - Comprehensive request validation
- **Rate Limiting** - API rate limiting via Nginx
- **CORS Protection** - Configured CORS policies
- **Security Headers** - Standard security headers
- **SSL/TLS** - HTTPS encryption with Let's Encrypt
- **Non-root Container** - Docker security best practices

## 📊 Database Schema

### Firestore Collections

#### `users` - User Profiles
```json
{
  "uid": "firebase_uid",
  "email": "user@email.com",
  "name": "User Name",
  "photoUrl": "https://...",
  "careerGoal": "frontend-developer",
  "experienceLevel": "beginner",
  "onboardingCompleted": true,
  "createdAt": "timestamp",
  "lastLoginAt": "timestamp"
}
```

#### `skills_master` - Global Skill Catalog
```json
{
  "skillId": "react",
  "name": "React",
  "category": "Frontend",
  "type": "technical",
  "aliases": ["reactjs", "react.js"],
  "prerequisites": ["javascript"],
  "relatedSkills": ["redux", "nextjs"],
  "levels": ["beginner", "intermediate", "advanced"]
}
```

#### `user_skills` - User Skill Tracking
```json
{
  "uid": "firebase_uid",
  "skillId": "react",
  "level": "intermediate",
  "confidence": "medium",
  "source": "self-reported",
  "lastUpdatedAt": "timestamp"
}
```

#### `user_roadmaps` - AI-Generated Learning Paths
```json
{
  "uid": "firebase_uid",
  "roleId": "frontend-developer",
  "roadmapVersion": "ai-generated",
  "generatedAt": "timestamp",
  "milestones": [
    {
      "title": "JavaScript Foundations",
      "description": "Core programming concepts",
      "skills": [
        {
          "skillId": "javascript",
          "targetLevel": "intermediate",
          "status": "in_progress",
          "completed": false
        }
      ]
    }
  ],
  "isActive": true
}
```

## 🔌 API Endpoints

### Authentication
- `POST /auth/login` - Firebase Google login
- `GET /auth/me` - Get current user
- `POST /auth/verify` - Verify token

### User Management
- `GET /users/profile` - Get user profile
- `PUT /users/profile` - Update profile
- `POST /users/onboarding` - Complete onboarding
- `GET /users/stats` - Get user statistics

### Skills Management
- `GET /skills` - Get skills (master or user)
- `POST /skills` - Add user skill
- `PUT /skills/{skillId}` - Update skill level
- `DELETE /skills/{skillId}` - Remove skill
- `GET /skills/categories` - Get skill categories
- `GET /skills/{skillId}/related` - Get related skills
- `GET /skills/analyze/{roleId}` - Analyze skill gaps

### AI Roadmaps
- `POST /roadmap/generate` - Generate AI roadmap
- `GET /roadmap` - Get active roadmap
- `PUT /roadmap/progress` - Update progress
- `GET /roadmap/templates` - Get templates
- `POST /roadmap/reset` - Reset roadmap

### Learning Resources
- `GET /learning/{skillId}` - Get resources for skill
- `GET /learning/search` - Search resources
- `GET /learning/category/{category}` - Resources by category
- `POST /learning/complete` - Mark resource completed
- `GET /learning/completions` - Get user completions
- `GET /learning/stats` - Learning statistics
- `GET /learning/recommendations` - Recommended resources

### Job Search
- `GET /jobs/search` - Search jobs
- `GET /jobs/recommendations` - Personalized job recommendations
- `GET /jobs/trending` - Trending roles
- `GET /jobs/countries` - Supported countries
- `GET /jobs/stats` - Job market statistics

### Activity Tracking
- `GET /activity` - Get user activity
- `GET /activity/types` - Activity types
- `GET /activity/summary` - Activity summary

### Settings
- `GET /settings` - Get user settings
- `PUT /settings` - Update settings
- `POST /settings/reset` - Reset to defaults
- `GET /settings/export` - Export settings

## 🤖 AI Integration

### Gemini 2.0 Flash Integration

The backend uses Google's Gemini 2.0 Flash model for AI-powered roadmap generation:

```python
# Example AI prompt structure
prompt = f"""
You are a career development AI creating a personalized learning roadmap for a {target_role} role.

USER PROFILE:
- Target Role: {target_role}
- Experience Level: {experience_level}
- Current Skills: {user_skills}

REQUIREMENTS:
1. Create 4-6 learning milestones
2. Each milestone should have 2-4 skills
3. Order skills by learning dependency
4. Use ONLY skill IDs from the valid list
5. Include beginner to advanced progression

OUTPUT FORMAT (JSON only):
{
  "milestones": [...]
}
"""
```

### AI Features
- **Skill Gap Analysis** - Intelligent skill matching and gap identification
- **Personalized Roadmaps** - Custom learning paths based on user profile
- **Resource Recommendations** - AI-curated learning materials
- **Progress Optimization** - Adaptive learning suggestions

## 📧 Email System

Automated email notifications for:
- Welcome emails for new users
- Roadmap generation notifications
- Weekly progress summaries
- Feedback confirmations

## 🚀 Deployment

### Google Cloud VM Deployment

1. **Create VM Instance**
```bash
gcloud compute instances create skillbridge-backend \
    --zone=us-central1-a \
    --machine-type=e2-medium \
    --image-family=ubuntu-2004-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB
```

2. **Setup Docker**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

3. **Deploy Application**
```bash
# Clone repository
git clone <repository-url>
cd backend

# Setup environment
cp .env.example .env
# Edit .env with production values

# Setup SSL certificates (Let's Encrypt)
sudo apt install certbot
sudo certbot certonly --standalone -d api.skillbridge.app

# Copy certificates to ssl directory
sudo cp /etc/letsencrypt/live/api.skillbridge.app/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/api.skillbridge.app/privkey.pem ssl/

# Deploy with Docker Compose
docker-compose up -d
```

4. **Setup Firewall**
```bash
# Allow HTTP and HTTPS
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

## 📈 Monitoring & Logging

- **Health Checks** - Built-in health check endpoint
- **Application Logs** - Structured logging with Python logging
- **Container Logs** - Docker container logging
- **Nginx Logs** - Access and error logs
- **Performance Monitoring** - Request timing and error tracking

## 🧪 Testing

```bash
# Run tests (when implemented)
python -m pytest tests/

# Test API endpoints
curl -X GET http://localhost:8000/health
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"idToken": "firebase_id_token"}'
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask secret key | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | Firebase service account path | Yes |
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `ADZUNA_APP_ID` | Adzuna API application ID | Yes |
| `ADZUNA_APP_KEY` | Adzuna API key | Yes |
| `SMTP_HOST` | SMTP server host | No |
| `SMTP_USER` | SMTP username | No |
| `SMTP_PASSWORD` | SMTP password | No |

### Firebase Configuration

1. Enable Authentication with Google provider
2. Create Firestore database in Native mode
3. Set up security rules for Firestore
4. Generate service account key

### Gemini AI Setup

1. Enable Gemini API in Google Cloud Console
2. Create API key with Gemini access
3. Set appropriate quotas and limits

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

## 🔄 Version History

- **v1.0.0** - Initial production release
  - Firebase Google authentication
  - AI-powered roadmap generation
  - Complete REST API
  - Docker deployment ready
  - Production security features

---

**SkillBridge Suite Backend** - Empowering careers through AI-driven learning paths 🚀