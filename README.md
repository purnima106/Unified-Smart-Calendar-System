# Unified Smart Calendar System

A comprehensive calendar management platform that unifies Google Calendar and Microsoft Outlook/Teams calendars, providing conflict detection, free time slot suggestions, and intelligent scheduling insights.

## 🎯 Problem Solved

Users often have meetings across multiple calendar platforms (Google Calendar, Microsoft Outlook/Teams) and face these challenges:
- **Fragmented View**: Must check each calendar separately
- **Hidden Conflicts**: Overlapping meetings across platforms are hard to spot
- **Poor Scheduling**: No centralized way to find available time slots
- **Time Waste**: Manual coordination between different calendar systems

## 🚀 Solution

A unified calendar platform that:
- **Connects** to multiple calendar providers (Google, Microsoft)
- **Syncs** and merges events into a unified database
- **Detects** conflicts automatically across all calendars
- **Suggests** optimal meeting times and free slots
- **Provides** analytics and productivity insights

## ✨ Key Features

### 🔐 Authentication & Integration
- OAuth login with Google and Microsoft
- **Multiple account support**: Connect multiple Google and Microsoft accounts to a single user profile
- **No account limit**: Add as many different calendar accounts as needed
- Secure token management and refresh
- Multi-provider calendar synchronization

### 📅 Unified Calendar View
- Single interface for all calendar events
- Color-coded events by provider (Google/Microsoft)
- Conflict highlighting with visual indicators
- FullCalendar.js integration with multiple view options

### ⚠️ Conflict Detection
- Automatic overlap detection across all calendars
- Detailed conflict analysis and reporting
- Conflict resolution suggestions
- Real-time conflict monitoring

### 🕐 Smart Scheduling
- Free time slot discovery
- Meeting time suggestions based on availability
- Customizable search parameters (duration, time range)
- AI-powered scheduling recommendations

### 📊 Analytics & Insights
- Calendar productivity scoring
- Meeting time analysis
- Conflict rate tracking
- Provider usage statistics
- Busiest day identification

## 🛠️ Tech Stack

### Backend
- **Framework**: Flask 3.1.2 (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: Flask-Login with OAuth
- **APIs**: Google Calendar API, Microsoft Graph API
- **Architecture**: MVC pattern with service layer

### Frontend
- **Framework**: React 19.1.1 with Vite
- **Styling**: Tailwind CSS with custom components
- **Calendar**: FullCalendar.js with multiple view plugins
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **Routing**: React Router DOM

### DevOps & Tools
- **Package Management**: pip (Python), npm (Node.js)
- **Development**: Hot reload with Vite
- **CORS**: Cross-origin resource sharing enabled
- **Environment**: Environment variable configuration

## 📁 Project Structure

```
Unified_Smart_Calendar_System/
├── backend/                    # Flask API Server
│   ├── app.py                 # Main Flask application
│   ├── config.py             # Configuration settings
│   ├── requirements.txt      # Python dependencies
│   ├── README.md            # Backend documentation
│   ├── models/              # Database models
│   │   ├── user_model.py    # User model with OAuth tokens
│   │   └── event_model.py   # Event model for calendar events
│   ├── services/            # Business logic services
│   │   ├── google_service.py      # Google Calendar integration
│   │   ├── microsoft_service.py   # Microsoft Calendar integration
│   │   └── conflict_service.py    # Conflict detection and free slots
│   └── controllers/         # API route handlers
│       ├── auth_controller.py     # Authentication endpoints
│       └── calendar_controller.py # Calendar operation endpoints
├── frontend/                   # React Application
│   ├── package.json         # Node.js dependencies
│   ├── vite.config.js       # Vite configuration
│   ├── tailwind.config.js   # Tailwind CSS configuration
│   ├── index.html          # HTML template
│   └── src/                # React source code
│       ├── main.jsx        # React entry point
│       ├── App.jsx         # Main application component
│       ├── index.css       # Global styles with Tailwind
│       ├── services/       # API service layer
│       │   └── api.js      # HTTP client and API functions
│       └── components/     # React components
│           ├── LoginPage.jsx       # OAuth login interface
│           ├── Dashboard.jsx       # Main dashboard view
│           ├── CalendarView.jsx    # FullCalendar integration
│           ├── ConflictsView.jsx   # Conflict management
│           ├── FreeSlotsView.jsx   # Free time slot finder
│           ├── SummaryView.jsx     # Analytics and insights
│           ├── Navbar.jsx          # Navigation component
│           └── LoadingSpinner.jsx  # Loading indicator
└── README.md                   # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL database
- Google Cloud Console project (for Google Calendar API)
- Microsoft Azure App Registration (for Microsoft Graph API)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Unified_Smart_Calendar_System
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set up environment variables
# Create .env file with VITE_API_URL=http://localhost:5000/api
```

### 4. Database Setup

```sql
CREATE DATABASE unified_calendar;
```

### 5. API Configuration

#### Google Calendar API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs: `http://localhost:5000/api/auth/auth/google/callback`
6. Copy Client ID and Client Secret to `.env`

#### Microsoft Graph API
1. Go to [Azure Portal](https://portal.azure.com/)
2. Register a new application
3. Add API permissions for Microsoft Graph (Calendars.Read)
4. Create a client secret
5. Add redirect URI: `http://localhost:5000/api/auth/auth/microsoft/callback`
6. Copy Application ID, Client Secret, and Tenant ID to `.env`

### 6. Run the Application

#### Start Backend
```bash
cd backend
python app.py
# Server runs on http://localhost:5000
```

#### Start Frontend
```bash
cd frontend
npm run dev
# Application runs on http://localhost:5173
```

## 📖 Usage Guide

### 1. Authentication
- Visit the application and click "Continue with Google" or "Continue with Microsoft"
- Complete OAuth flow to connect your calendar
- You can connect both providers for full functionality

#### Multiple Account Support
- **Adding Multiple Accounts**: After logging in, use the "+ Add Google Account" or "+ Add Microsoft Account" buttons in the Dashboard to connect additional calendar accounts
- **Account Limits**: 
  - **No hard limit** on the number of accounts you can add
  - You can connect multiple different email addresses (e.g., personal@gmail.com, work@gmail.com, company@outlook.com)
  - The same email address cannot be added twice - the system will update the existing connection instead
- **Managing Accounts**: View all connected accounts in the Dashboard, see sync status, and remove accounts as needed
- **Unified View**: All events from all connected accounts appear in your unified calendar view

### 2. Dashboard
- View calendar connection status
- See quick statistics and summary
- Access quick actions for common tasks
- Sync all connected calendars

### 3. Calendar View
- Browse unified calendar with all events
- Events are color-coded by provider
- Conflicts are highlighted in red
- Click events for detailed information
- Switch between month, week, day, and list views

### 4. Conflict Management
- View all detected conflicts
- See detailed conflict information
- Get resolution suggestions
- Track conflict patterns over time

### 5. Free Time Slots
- Search for available meeting times
- Customize duration and time range
- Get AI-powered meeting suggestions
- Schedule meetings directly from available slots

### 6. Analytics
- View calendar productivity score
- Analyze meeting patterns
- Track conflict rates
- Get personalized insights and recommendations

## 🔧 API Endpoints

### Authentication
- `GET /api/auth/login/google` - Initiate Google OAuth (adds account if already logged in)
- `GET /api/auth/login/microsoft` - Initiate Microsoft OAuth (adds account if already logged in)
- `GET /api/auth/logout` - Logout user
- `GET /api/auth/user/profile` - Get user profile
- `GET /api/auth/user/connections` - Get calendar connections (supports multiple accounts)
- `GET /api/auth/user/connections/list` - Get detailed list of all connections
- `DELETE /api/auth/user/connections/{id}` - Remove a connection

### Calendar Operations
- `GET /api/calendar/events` - Get all events
- `POST /api/calendar/sync/all` - Sync all calendars
- `GET /api/calendar/conflicts` - Get conflicts
- `GET /api/calendar/free-slots` - Find free time slots
- `POST /api/calendar/suggest-meeting` - Get meeting suggestions
- `GET /api/calendar/summary` - Get analytics summary

## 🎨 UI/UX Features

### Modern Design
- Clean, responsive interface with Tailwind CSS
- Mobile-friendly design
- Smooth animations and transitions
- Intuitive navigation

### Visual Indicators
- Color-coded events by provider
- Conflict highlighting
- Status badges and icons
- Progress indicators and loading states

### User Experience
- Real-time updates
- Error handling with user-friendly messages
- Loading states and skeleton screens
- Responsive feedback for all actions

## 🔒 Security Features

- OAuth 2.0 authentication
- Secure token storage and refresh
- CORS configuration
- Input validation and sanitization
- Environment variable protection

## 🚀 Deployment

### Production Considerations
1. Use HTTPS in production
2. Set up proper environment variables
3. Configure database connection pooling
4. Use production WSGI server (Gunicorn)
5. Set up proper logging
6. Configure CORS for production domains

### Docker Deployment
```dockerfile
# Backend Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the documentation in each component
- Review the API endpoints
- Check the troubleshooting section in backend README

## 🔮 Future Enhancements

- [ ] Real-time notifications for conflicts
- [ ] Advanced conflict resolution workflows
- [ ] Calendar sharing and collaboration
- [ ] Mobile app development
- [ ] Integration with more calendar providers
- [ ] Advanced analytics and reporting
- [ ] Meeting optimization suggestions
- [ ] Calendar health scoring

---

**Built with ❤️ for better calendar management**
