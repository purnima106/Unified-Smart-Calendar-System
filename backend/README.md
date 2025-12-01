# Unified Smart Calendar System - Backend

A Flask-based backend API for the Unified Smart Calendar System that integrates Google Calendar and Microsoft Outlook/Teams calendars.

## Features

- 🔐 OAuth authentication with Google and Microsoft
- 📅 Calendar event synchronization from multiple providers
- ⚠️ Conflict detection for overlapping events
- 🕐 Free time slot suggestions
- 📊 Calendar analytics and summaries
- 🗄️ PostgreSQL database with SQLAlchemy ORM

## Tech Stack

- **Framework**: Flask 3.1.2
- **Database**: PostgreSQL with SQLAlchemy
- **Authentication**: Flask-Login with OAuth
- **APIs**: Google Calendar API, Microsoft Graph API
- **CORS**: Flask-CORS for frontend integration

## Setup Instructions

### 1. Prerequisites

- Python 3.8+
- PostgreSQL database
- Google Cloud Console project (for Google Calendar API)
- Microsoft Azure App Registration (for Microsoft Graph API)

### 2. Environment Configuration

Create a `.env` file in the backend directory with the following variables:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here-change-in-production
FLASK_ENV=development
FLASK_DEBUG=1

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost/unified_calendar

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/api/auth/auth/google/callback

# Microsoft OAuth Configuration
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
MICROSOFT_REDIRECT_URI=http://localhost:5000/api/auth/auth/microsoft/callback
MICROSOFT_TENANT_ID=your-microsoft-tenant-id

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
```

### 3. Google Calendar API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs
6. Copy Client ID and Client Secret to `.env` file

### 4. Microsoft Graph API Setup

1. Go to [Azure Portal](https://portal.azure.com/)
2. Register a new application
3. Add API permissions for Microsoft Graph (Calendars.Read)
4. Create a client secret
5. Copy Application ID, Client Secret, and Tenant ID to `.env` file

### 5. Database Setup

```sql
CREATE DATABASE unified_calendar;
```

### 6. Installation

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

## API Endpoints

### Authentication

- `GET /api/auth/login/google` - Initiate Google OAuth
- `GET /api/auth/auth/google/callback` - Google OAuth callback
- `GET /api/auth/login/microsoft` - Initiate Microsoft OAuth
- `GET /api/auth/auth/microsoft/callback` - Microsoft OAuth callback
- `GET /api/auth/logout` - Logout user
- `GET /api/auth/user/profile` - Get user profile
- `GET /api/auth/user/connections` - Get calendar connections

### Calendar Operations

- `GET /api/calendar/events` - Get all events
- `GET /api/calendar/events/<id>` - Get specific event
- `POST /api/calendar/sync/google` - Sync Google Calendar events
- `POST /api/calendar/sync/microsoft` - Sync Microsoft Calendar events
- `POST /api/calendar/sync/all` - Sync all connected calendars
- `GET /api/calendar/conflicts` - Get calendar conflicts
- `GET /api/calendar/free-slots` - Get free time slots
- `POST /api/calendar/suggest-meeting` - Suggest meeting times
- `GET /api/calendar/summary` - Get calendar summary

## Project Structure

```
backend/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── models/              # Database models
│   ├── user_model.py    # User model with OAuth tokens
│   └── event_model.py   # Event model for calendar events
├── services/            # Business logic services
│   ├── google_service.py      # Google Calendar integration
│   ├── microsoft_service.py   # Microsoft Calendar integration
│   └── conflict_service.py    # Conflict detection and free slots
└── controllers/         # API route handlers
    ├── auth_controller.py     # Authentication endpoints
    └── calendar_controller.py # Calendar operation endpoints
```

## Database Models

### User Model
- Stores user information and OAuth tokens
- Tracks calendar connection status
- Manages user sessions

### Event Model
- Stores calendar events from all providers
- Handles conflict detection
- Supports event metadata and attendees

## Services

### Google Calendar Service
- OAuth authentication flow
- Event synchronization
- Token refresh management

### Microsoft Calendar Service
- OAuth authentication flow
- Microsoft Graph API integration
- Event synchronization

### Conflict Detection Service
- Overlap detection algorithm
- Free time slot calculation
- Meeting time suggestions
- Calendar analytics

## Development

### Running in Development Mode

```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py
```

### Database Migrations

The application uses SQLAlchemy with automatic table creation. For production, consider using Flask-Migrate for database migrations.

### Testing

```bash
# Run tests (when implemented)
python -m pytest tests/
```

## Production Deployment

1. Set `FLASK_ENV=production`
2. Use a production WSGI server (Gunicorn, uWSGI)
3. Configure proper CORS origins
4. Use environment variables for all sensitive data
5. Set up proper logging
6. Configure database connection pooling

## Security Considerations

- Store OAuth tokens securely
- Use HTTPS in production
- Implement proper session management
- Validate all input data
- Use environment variables for secrets
- Implement rate limiting for API endpoints

## Troubleshooting

### Common Issues

1. **Database Connection**: Ensure PostgreSQL is running and credentials are correct
2. **OAuth Errors**: Verify redirect URIs match exactly
3. **CORS Issues**: Check CORS_ORIGINS configuration
4. **Token Expiry**: Implement proper token refresh logic

### Logs

Check application logs for detailed error information:

```bash
tail -f logs/app.log
```

## Contributing

1. Follow PEP 8 style guidelines
2. Add proper docstrings to functions
3. Write tests for new features
4. Update documentation as needed

## License

This project is part of the Unified Smart Calendar System.
