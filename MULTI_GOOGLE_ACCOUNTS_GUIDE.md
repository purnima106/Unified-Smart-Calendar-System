# Multi-Google Account Feature

## Overview

The system now supports connecting **multiple Google Calendar accounts** to a single user account. This allows you to:
- Sync events from multiple Google accounts
- View all events in a unified calendar
- Manage each account independently
- Add/remove Google accounts as needed

---

## How It Works

### Architecture Changes

1. **New Model: `CalendarConnection`**
   - Stores OAuth tokens for each connected account
   - Links to User model (one user can have many connections)
   - Tracks account email, name, and sync status
   - Supports both Google and Microsoft (when enabled)

2. **Backward Compatibility**
   - Legacy User model still works
   - Existing single-account users continue to work
   - System automatically falls back to legacy sync if no connections found

3. **Event Uniqueness**
   - Events are identified by: `{account_email}:{event_id}`
   - Prevents conflicts between accounts with same event IDs
   - Each account's events are tracked separately

---

## Features

### ✅ Add Multiple Google Accounts

1. **From Dashboard:**
   - Click "Add Google Account" button
   - Complete Google OAuth flow
   - Account is automatically added and synced

2. **From Login:**
   - If already logged in, clicking "Continue with Google" adds another account
   - If not logged in, creates user and adds first account

### ✅ View All Connected Accounts

- Dashboard shows all connected Google accounts
- Each account displays:
  - Account name and email
  - Connection status
  - Last sync timestamp
  - Remove button

### ✅ Sync All Accounts

- **"Sync All" button** syncs events from:
  - All active Google accounts
  - All active Microsoft accounts (if enabled)
- Each account syncs independently
- Results show per-account sync counts

### ✅ Remove Accounts

- Click trash icon next to any account
- Confirms before removal
- Soft delete (marks as inactive, doesn't delete data)
- Events from removed account remain in database

---

## API Endpoints

### Authentication

- `GET /api/auth/login/google` - Initiate Google OAuth (adds account if logged in)
- `GET /api/auth/google/callback` - Handle OAuth callback

### Connection Management

- `GET /api/auth/user/connections` - Get all connections (grouped by provider)
- `GET /api/auth/user/connections/list` - Get detailed list of all connections
- `DELETE /api/auth/user/connections/{id}` - Remove a connection
- `POST /api/auth/user/connections/{id}/toggle` - Enable/disable a connection

### Sync

- `POST /api/calendar/sync/google` - Sync all Google accounts
- `POST /api/calendar/sync/all` - Sync all accounts (Google + Microsoft)

---

## Database Schema

### CalendarConnection Table

```sql
CREATE TABLE calendar_connections (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    provider VARCHAR(20) NOT NULL,  -- 'google' or 'microsoft'
    provider_account_email VARCHAR(200) NOT NULL,
    provider_account_name VARCHAR(200),
    token TEXT NOT NULL,  -- JSON OAuth token
    is_connected BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    calendar_id VARCHAR(100) DEFAULT 'primary',
    last_synced DATETIME,
    created_at DATETIME,
    updated_at DATETIME
);
```

### Event Table Update

- `provider_event_id` increased from 100 to 200 characters
- Format: `{account_email}:{original_event_id}`
- Example: `user1@gmail.com:abc123xyz`

---

## Usage Examples

### Adding a Second Google Account

1. Log in with your first Google account
2. Go to Dashboard
3. Click "Add Google Account"
4. Complete Google OAuth
5. Account appears in connected accounts list
6. Click "Sync All" to sync events from both accounts

### Viewing Events from Multiple Accounts

- All events appear in the unified Calendar View
- Events are color-coded by provider
- Each event shows which account it came from (via organizer field)

### Removing an Account

1. Go to Dashboard
2. Find the account you want to remove
3. Click the trash icon
4. Confirm removal
5. Account is marked inactive
6. Events remain but won't sync anymore

---

## Migration Notes

### For Existing Users

- Existing single-account users continue to work
- System uses legacy User model if no CalendarConnection found
- No data migration required
- New accounts automatically use CalendarConnection model

### Database Migration

The `CalendarConnection` table is created automatically when you start the app:
```python
# In app.py
from models.calendar_connection_model import CalendarConnection
db.create_all()  # Creates table if it doesn't exist
```

---

## Technical Details

### OAuth Flow

1. User clicks "Add Google Account"
2. Redirected to Google OAuth
3. User authorizes
4. Callback creates/updates CalendarConnection
5. Auto-syncs events for new connection
6. Returns to Dashboard

### Sync Process

1. Finds all active Google connections
2. For each connection:
   - Gets OAuth token
   - Refreshes if expired
   - Calls Google Calendar API
   - Downloads events (30 days back, 30 days forward)
   - Stores with unique ID: `{email}:{event_id}`
   - Updates last_synced timestamp

### Event Storage

- Events stored with `user_id` (same for all accounts)
- `provider_event_id` includes account email for uniqueness
- `organizer` field stores account email
- Events can be filtered by account if needed

---

## Troubleshooting

### Issue: "Account not syncing"

**Solution:**
1. Check if account is active: `is_active = true`
2. Check OAuth token: May need to re-authenticate
3. Check last_synced timestamp
4. Try manual sync from Dashboard

### Issue: "Duplicate events"

**Solution:**
- Events are uniquely identified by `{email}:{event_id}`
- If duplicates appear, check provider_event_id format
- May need to clear and re-sync

### Issue: "Can't add account"

**Solution:**
1. Check if already connected (same email)
2. Check OAuth configuration
3. Clear browser cookies and try again
4. Check backend logs for errors

---

## Future Enhancements

- [ ] Sync specific calendars (not just primary)
- [ ] Account-specific sync schedules
- [ ] Per-account event filtering
- [ ] Account labels/names
- [ ] Sync status per account
- [ ] Bulk account management

---

## Summary

✅ **Multiple Google accounts supported**
✅ **Backward compatible with single accounts**
✅ **Easy to add/remove accounts**
✅ **Unified calendar view**
✅ **Independent sync per account**

The system now fully supports multiple Google Calendar accounts while maintaining compatibility with existing single-account setups.

