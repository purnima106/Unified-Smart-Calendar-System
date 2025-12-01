# Microsoft Calendar Integration - Temporarily Disabled

## Overview

Microsoft Calendar integration has been **temporarily disabled** to prevent tenant-wide event notifications when using company tenant IDs. The system now operates in **Google Calendar-only mode**.

---

## What Changed

### Backend Changes

1. **Configuration Flag Added** (`backend/config.py`)
   - New setting: `MICROSOFT_ENABLED` (defaults to `false`)
   - Set via environment variable: `MICROSOFT_ENABLED=true` to re-enable

2. **Disabled Endpoints**
   - `/api/auth/login/microsoft` - Returns 503 with disabled message
   - `/api/auth/microsoft/callback` - Returns 503 with disabled message
   - `/api/calendar/sync/microsoft` - Returns 503 with disabled message
   - `/api/calendar/sync/bidirectional` - Returns 503 (requires both providers)

3. **Modified Endpoints**
   - `/api/calendar/sync/all` - Only syncs Google calendars
   - `/api/calendar/sync/view-only` - Only syncs Google calendars
   - `/api/calendar/create-event` - Defaults to Google-only, ignores Microsoft requests

4. **Health Check Updated**
   - Shows Microsoft status as "disabled (temporarily)"

### Frontend Changes

1. **Login Page** (`frontend/src/components/LoginPage.jsx`)
   - Microsoft login button marked as `available: false`
   - Button shows "Microsoft (Coming Soon)" and is disabled

2. **Dashboard** (`frontend/src/components/Dashboard.jsx`)
   - Microsoft connection status card removed
   - Only shows Google Calendar connection

3. **Navbar** (`frontend/src/components/Navbar.jsx`)
   - Microsoft badge removed
   - Only shows Google connection status

---

## Current Configuration

### Environment Variable

In `backend/.env`, Microsoft is disabled by default:

```env
# Microsoft is disabled by default
# Set to 'true' to re-enable (not recommended with company tenant)
MICROSOFT_ENABLED=false
```

**Note**: Even if you don't set this variable, it defaults to `false`, so Microsoft is disabled.

---

## How It Works Now

### ✅ What Still Works

- **Google Calendar Login** - Fully functional
- **Google Calendar Sync** - Works normally
- **Google Event Creation** - Creates events in Google Calendar
- **Conflict Detection** - Works with Google events
- **Free Slots** - Works with Google calendar data
- **Calendar Summary** - Shows Google calendar analytics
- **Unified Calendar View** - Displays Google events

### ❌ What's Disabled

- Microsoft Calendar login
- Microsoft Calendar sync
- Bidirectional sync (Google ↔ Microsoft)
- Microsoft event creation
- Any Microsoft-related features

---

## Testing Google-Only Mode

1. **Start Backend**
   ```bash
   cd backend
   python app.py
   ```

2. **Start Frontend**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Test Login**
   - Go to http://localhost:5173
   - You should only see "Continue with Google" button
   - Microsoft button should be disabled/grayed out

4. **Test Sync**
   - After logging in with Google
   - Click "Sync All" on Dashboard
   - Should only sync Google Calendar
   - No Microsoft sync should occur

5. **Check Health Endpoint**
   ```bash
   curl http://localhost:5000/health
   ```
   Should show:
   ```json
   {
     "microsoft_enabled": false,
     "oauth_configuration": {
       "google": "configured",
       "microsoft": "disabled (temporarily)"
     }
   }
   ```

---

## Re-enabling Microsoft (When Ready)

### Step 1: Update Configuration

Edit `backend/.env`:
```env
MICROSOFT_ENABLED=true
```

### Step 2: Restore Frontend

Uncomment Microsoft-related code in:
- `frontend/src/components/LoginPage.jsx` - Set `available: true`
- `frontend/src/components/Dashboard.jsx` - Uncomment Microsoft status card
- `frontend/src/components/Navbar.jsx` - Uncomment Microsoft badge

### Step 3: Restart Services

```bash
# Restart backend
cd backend
python app.py

# Restart frontend
cd frontend
npm run dev
```

---

## Why This Was Done

1. **Tenant-Wide Notifications**: Using company tenant ID caused all employees to receive event reminders
2. **Privacy Concerns**: Company calendar data was being accessed
3. **Personal Account Needed**: Requires personal Microsoft account (not company email)

---

## Troubleshooting

### Issue: "Microsoft button still shows"
**Solution**: Clear browser cache and restart frontend

### Issue: "Microsoft sync still happening"
**Solution**: 
1. Check `backend/.env` has `MICROSOFT_ENABLED=false`
2. Restart backend server
3. Verify with: `curl http://localhost:5000/health`

### Issue: "Bidirectional sync button still works"
**Solution**: The button is disabled in the frontend, but if you call the API directly, it will return a 503 error with a clear message.

---

## Summary

✅ **Microsoft is now disabled**
✅ **Google Calendar works normally**
✅ **All Google features functional**
✅ **Easy to re-enable when needed**

The system is now safe to use with Google Calendar only, without any risk of sending notifications to company employees.

