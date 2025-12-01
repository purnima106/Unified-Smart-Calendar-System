# OAuth Setup Guide for Real Google and Microsoft Calendar Integration

## Prerequisites
- Google Cloud Console account
- Microsoft Azure account
- Backend server running on http://localhost:5000
- Frontend server running on http://localhost:5173

## Step 1: Google OAuth Setup

### 1.1 Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Calendar API:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Calendar API"
   - Click "Enable"

### 1.2 Configure OAuth Consent Screen
1. Go to "APIs & Services" → "OAuth consent screen"
2. Choose "External" user type
3. Fill in required information:
   - App name: "Unified Smart Calendar System"
   - User support email: Your email
   - Developer contact information: Your email
4. Add scopes:
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`

### 1.3 Create OAuth Credentials
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client IDs"
3. Choose "Web application"
4. Set authorized redirect URIs:
   - `http://localhost:5000/oauth2callback`
5. Set authorized JavaScript origins:
   - `http://localhost:5173`
6. Copy the Client ID and Client Secret

## Step 2: Microsoft OAuth Setup

### 2.1 Register Application in Azure
1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to "Azure Active Directory" → "App registrations"
3. Click "New registration"
4. Fill in details:
   - Name: "Unified Smart Calendar System"
   - Supported account types: "Accounts in any organizational directory and personal Microsoft accounts"
   - Redirect URI: `http://localhost:5000/api/auth/microsoft/callback` (Web)

### 2.2 Configure API Permissions
1. Go to "API permissions"
2. Click "Add a permission"
3. Select "Microsoft Graph"
4. Choose "Delegated permissions"
5. Add these permissions:
   - `Calendars.Read`
   - `User.Read`
   - `email`
   - `profile`
6. Click "Grant admin consent"

### 2.3 Create Client Secret
1. Go to "Certificates & secrets"
2. Click "New client secret"
3. Add description and choose expiration
4. Copy the secret value immediately (you won't see it again)

### 2.4 Get Application (Client) ID and Tenant ID
1. From the app registration overview, copy:
   - Application (client) ID
   - Directory (tenant) ID

## Step 3: Configure Environment Variables

Create a `.env` file in the `backend` directory with your real credentials:

```env
# Flask Configuration
SECRET_KEY=your-super-secret-key-change-this-in-production
DATABASE_URL=sqlite:///unified_calendar.db

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-actual-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-actual-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/oauth2callback

# Microsoft OAuth Configuration
MICROSOFT_CLIENT_ID=your-actual-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-actual-microsoft-client-secret
MICROSOFT_TENANT_ID=your-actual-tenant-id
MICROSOFT_REDIRECT_URI=http://localhost:5000/api/auth/microsoft/callback
```

## Step 4: Update Frontend for Real OAuth

The frontend needs to be updated to use real OAuth instead of sample data. The current setup uses mock users, but we need to implement proper OAuth flow.

### 4.1 Update Login Component
The login page should redirect users to the real OAuth endpoints:
- Google: `http://localhost:5000/api/auth/login/google`
- Microsoft: `http://localhost:5000/api/auth/login/microsoft`

### 4.2 Handle OAuth Callbacks
The backend will redirect users back to the frontend after successful OAuth.

## Step 5: Test the Integration

1. Start the backend server:
   ```bash
   cd backend
   python app.py
   ```

2. Start the frontend server:
   ```bash
   cd frontend
   npm run dev
   ```

3. Navigate to http://localhost:5173
4. Click "Connect Google Calendar" or "Connect Microsoft Calendar"
5. Complete the OAuth flow
6. Your real calendar events should appear in the unified view

## Troubleshooting

### Common Issues:
1. **"Invalid redirect URI"**: Make sure the redirect URIs in your OAuth apps match exactly
2. **"Scope not authorized"**: Ensure all required scopes are added to the OAuth consent screen
3. **"Client ID not found"**: Double-check your environment variables
4. **CORS errors**: Ensure the frontend origin is added to authorized JavaScript origins

### Debug Steps:
1. Check browser console for errors
2. Check backend logs for OAuth errors
3. Verify environment variables are loaded correctly
4. Test OAuth endpoints directly: `http://localhost:5000/api/auth/login/google`

## Security Notes

- Never commit your `.env` file to version control
- Use strong, unique client secrets
- Regularly rotate your OAuth credentials
- In production, use HTTPS for all OAuth redirects
- Consider implementing PKCE for additional security

## Next Steps

After setting up OAuth:
1. Implement proper user management
2. Add error handling for OAuth failures
3. Implement token refresh logic
4. Add calendar sync scheduling
5. Implement conflict detection with real data
