# Setup Instructions for Unified Smart Calendar System

## 1. Environment Configuration

Create a `.env` file in the `backend` directory with the following content:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here-change-this-in-production
DATABASE_URL=postgresql://localhost/unified_calendar

# Google OAuth Configuration
# Get these from Google Cloud Console: https://console.cloud.google.com/
# 1. Go to APIs & Services > Credentials
# 2. Create OAuth 2.0 Client ID
# 3. Add http://localhost:3000 to authorized JavaScript origins
# 4. Add http://localhost:5000/oauth2callback to authorized redirect URIs
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/oauth2callback


# Microsoft OAuth Configuration
# Get these from Azure Portal: https://portal.azure.com/
# 1. Go to Azure Active Directory > App registrations
# 2. Create new registration
# 3. Add http://localhost:3000 to redirect URIs
# 4. Get Client ID, Client Secret, and Tenant ID
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
MICROSOFT_TENANT_ID=your-tenant-id
MICROSOFT_REDIRECT_URI=http://localhost:5000/api/auth/microsoft/callback


# Frontend API URL
VITE_API_URL=http://localhost:5000/api
```

## 2. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Calendar API
4. Go to "APIs & Services" > "Credentials"
5. Click "Create Credentials" > "OAuth 2.0 Client ID"
6. Configure:
   - Application type: Web application
   - Authorized JavaScript origins: `http://localhost:3000`
   - Authorized redirect URIs: `http://localhost:5000/oauth2callback`
7. Copy Client ID and Client Secret to your `.env` file

## 3. Microsoft OAuth Setup

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to "Azure Active Directory" > "App registrations"
3. Click "New registration"
4. Configure:
   - Name: "Unified Calendar System"
   - Supported account types: "Accounts in this organizational directory only"
   - Redirect URI: Web > `http://localhost:3000`
5. After creation, note the Application (client) ID and Directory (tenant) ID
6. Go to "Certificates & secrets" > "New client secret"
7. Copy the secret value to your `.env` file
8. Go to "API permissions" > "Add permission" > "Microsoft Graph" > "Delegated permissions"
9. Add: `Calendars.Read`, `User.Read`
10. Click "Grant admin consent"

## 4. Database Setup

1. Install PostgreSQL if not already installed
2. Create database:
   ```sql
   CREATE DATABASE unified_calendar;
   ```
3. Run database initialization:
   ```bash
   cd backend
   python init_db.py
   ```

## 5. Running the Application

1. Start the backend:
   ```bash
   cd backend
   python app.py
   ```

2. Start the frontend (in a new terminal):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. Access the application at `http://localhost:3000`

## Troubleshooting

### Calendar Not Displaying
- Check if OAuth credentials are properly configured
- Verify database connection
- Check browser console for errors
- Ensure events are being synced from connected calendars

### Microsoft Sign-in Issues
- Verify all Microsoft environment variables are set
- Check Azure app registration permissions
- Ensure redirect URI matches exactly
- Check tenant ID is correct

### Google Sign-in Issues
- Verify Google Cloud Console configuration
- Check redirect URI matches exactly
- Ensure Google Calendar API is enabled
