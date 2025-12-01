# Manual Testing Checklist

Use this checklist to track your progress through manual testing. Check off items as you complete them.

## Pre-Testing Setup

### Environment Verification
- [ ] Backend server running on `http://localhost:5000`
- [ ] Frontend server running on `http://localhost:5173`
- [ ] PostgreSQL database connected and accessible
- [ ] Google OAuth credentials configured in `.env`
- [ ] Microsoft OAuth credentials configured in `.env`
- [ ] Database schema up-to-date
- [ ] Browser cache cleared
- [ ] Test browser: Chrome / Firefox / Edge

### Test Accounts Preparation
- [ ] Google Account 1 ready: ________________
- [ ] Google Account 2 ready: ________________
- [ ] Microsoft Account 1 ready: ________________
- [ ] Microsoft Account 2 ready: ________________
- [ ] Test events created in calendars
- [ ] Overlapping events created for conflict testing

---

## 1. Authentication & Account Management

### 1.1 Google OAuth Flow
- [ ] Navigate to landing page
- [ ] Click "Continue with Google"
- [ ] Complete Google authentication
- [ ] Verify redirect to dashboard
- [ ] Check user profile displays correctly
- [ ] Verify Google account in connections list
- [ ] Add second Google account
- [ ] Verify both accounts show

### 1.2 Microsoft OAuth Flow
- [ ] Click "Continue with Microsoft"
- [ ] Complete Microsoft authentication
- [ ] Verify redirect to dashboard
- [ ] Check user profile displays correctly
- [ ] Verify Microsoft account in connections list
- [ ] Add second Microsoft account
- [ ] Verify both accounts show

### 1.3 Multi-Account Scenarios
- [ ] Connect Google then Microsoft
- [ ] Connect Microsoft then Google
- [ ] Connect multiple Google accounts
- [ ] Connect multiple Microsoft accounts
- [ ] Verify all connections display correctly
- [ ] Test connection toggle
- [ ] Verify disabled connections don't sync

### 1.4 Session Management
- [ ] User stays logged in after refresh
- [ ] Logout works correctly
- [ ] Redirect to login after logout
- [ ] Session persists across tabs

**Notes:**
```
[Add any issues or observations here]
```

---

## 2. Calendar Synchronization

### 2.1 Google Calendar Sync
- [ ] Click "Sync Google" button
- [ ] Loading state displays
- [ ] Success message with sync count
- [ ] Events appear in calendar view
- [ ] `last_synced` timestamp updates
- [ ] Sync with multiple Google accounts
- [ ] Events from all accounts appear

### 2.2 Microsoft Calendar Sync
- [ ] Click "Sync Microsoft" button
- [ ] Loading state displays
- [ ] Success message with sync count
- [ ] Events appear in calendar view
- [ ] `last_synced` timestamp updates
- [ ] Sync with multiple Microsoft accounts
- [ ] Events from all accounts appear

### 2.3 Sync All Functionality
- [ ] Click "Sync All" button
- [ ] Both Google and Microsoft sync
- [ ] Combined sync count in response
- [ ] Events from all accounts appear
- [ ] Test with only Google connected
- [ ] Test with only Microsoft connected
- [ ] Test with both connected

### 2.4 Bidirectional Sync
- [ ] Click "Bidirectional Sync" button
- [ ] Loading state displays
- [ ] Success message
- [ ] Blocker events created in target calendars
- [ ] Events marked as `[Mirror] Busy`
- [ ] No notifications sent (check email)
- [ ] Test Google → Microsoft sync
- [ ] Test Microsoft → Google sync
- [ ] Test Google ↔ Google sync
- [ ] Test Microsoft ↔ Microsoft sync

### 2.5 Sync Error Handling
- [ ] Test with expired token (should refresh)
- [ ] Test with invalid credentials
- [ ] Test with network interruption
- [ ] Error messages display clearly
- [ ] Backend logs show error details

**Notes:**
```
[Add any issues or observations here]
```

---

## 3. Calendar View

### 3.1 Event Display
- [ ] Navigate to Calendar view
- [ ] All synced events display
- [ ] Events color-coded by provider
- [ ] Event titles display correctly
- [ ] Event times are accurate
- [ ] Event details on click
- [ ] Events from multiple accounts appear
- [ ] No duplicate events

### 3.2 Calendar Views
- [ ] Month view works
- [ ] Week view works
- [ ] Day view works
- [ ] List view works
- [ ] View switching smooth
- [ ] Navigation works (prev/next)
- [ ] Today button works
- [ ] Date picker works

### 3.3 Event Filtering
- [ ] Only future/current events show
- [ ] Events spanning multiple days display
- [ ] All-day events display correctly
- [ ] Events with different timezones work

### 3.4 Calendar Responsiveness
- [ ] Desktop (1920x1080) - OK
- [ ] Desktop (1366x768) - OK
- [ ] Tablet (768x1024) - OK
- [ ] Mobile (375x667) - OK
- [ ] Mobile (414x896) - OK
- [ ] Calendar adapts to screen size
- [ ] Touch interactions work on mobile

**Notes:**
```
[Add any issues or observations here]
```

---

## 4. Conflict Detection

### 4.1 Conflict Detection
- [ ] Navigate to Conflicts view
- [ ] Create overlapping events
- [ ] Run sync to detect conflicts
- [ ] Conflicts appear in Conflicts view
- [ ] Conflict details correct
- [ ] Conflict count matches overlaps
- [ ] Multiple conflicts detected

### 4.2 Conflict Scenarios
- [ ] Exact time overlap detected
- [ ] Partial overlap detected
- [ ] Conflicts from same provider
- [ ] Conflicts from different providers
- [ ] Conflicts across multiple accounts
- [ ] Conflicts update after new sync

### 4.3 Conflict Display
- [ ] Conflicts highlighted in calendar
- [ ] Conflict information clear
- [ ] Date range filtering works

**Notes:**
```
[Add any issues or observations here]
```

---

## 5. Free Slots Discovery

### 5.1 Basic Free Slots
- [ ] Navigate to Free Slots view
- [ ] Select a date
- [ ] Set duration (60 minutes)
- [ ] Click "Find Free Slots"
- [ ] Free slots display correctly
- [ ] Slots don't overlap with events
- [ ] Slot times are accurate

### 5.2 Advanced Free Slots
- [ ] Custom time range works
- [ ] Different durations work (30/60/120 min)
- [ ] Multiple accounts considered
- [ ] Slots consider all calendars
- [ ] Busy day shows fewer slots
- [ ] Empty day shows many slots

### 5.3 Meeting Suggestions
- [ ] Meeting time suggestion works
- [ ] Suggestions are optimal
- [ ] Suggestions avoid conflicts
- [ ] Different parameters work

**Notes:**
```
[Add any issues or observations here]
```

---

## 6. Summary & Analytics

### 6.1 Calendar Summary
- [ ] Navigate to Summary view
- [ ] Summary loads correctly
- [ ] Total events count correct
- [ ] Conflicts count matches
- [ ] Events by provider breakdown
- [ ] Date range displays correctly

### 6.2 Analytics Features
- [ ] Productivity score displays
- [ ] Meeting time analysis works
- [ ] Conflict rate tracking works
- [ ] Provider usage statistics correct
- [ ] Busiest day identified
- [ ] Different date ranges work

### 6.3 Summary Accuracy
- [ ] Summary stats match actual events
- [ ] Counts match calendar view
- [ ] Calculations are correct
- [ ] Empty calendar handled
- [ ] Heavily booked calendar handled

**Notes:**
```
[Add any issues or observations here]
```

---

## 7. Dashboard

### 7.1 Dashboard Display
- [ ] Dashboard loads after login
- [ ] Connection status cards display
- [ ] Last synced timestamps show
- [ ] Quick stats display correctly
- [ ] Action buttons functional

### 7.2 Quick Actions
- [ ] "Sync All" from dashboard works
- [ ] "Bidirectional Sync" from dashboard works
- [ ] Navigation to other views works
- [ ] Loading states display

### 7.3 Connection Management
- [ ] All connections list correctly
- [ ] Connection toggle works
- [ ] Connection status updates
- [ ] Add new account flow works

**Notes:**
```
[Add any issues or observations here]
```

---

## 8. UI/UX

### 8.1 Navigation
- [ ] All navigation links work
- [ ] Active route highlighting works
- [ ] Back/forward browser buttons work
- [ ] Deep linking works

### 8.2 Visual Design
- [ ] Purple/white theme consistent
- [ ] Color coding correct (Google/Microsoft)
- [ ] Conflict highlighting (red) works
- [ ] Loading spinners display
- [ ] Error messages styled correctly

### 8.3 Responsive Design
- [ ] Chrome desktop - OK
- [ ] Chrome mobile - OK
- [ ] Firefox desktop - OK
- [ ] Firefox mobile - OK
- [ ] Edge desktop - OK
- [ ] Edge mobile - OK
- [ ] All views usable on mobile
- [ ] Touch targets adequate size

### 8.4 User Feedback
- [ ] Success messages display
- [ ] Error messages clear
- [ ] Loading states on all actions
- [ ] Form validation messages work

**Notes:**
```
[Add any issues or observations here]
```

---

## 9. Error Handling & Edge Cases

### 9.1 Network Errors
- [ ] Backend offline handled gracefully
- [ ] User-friendly error messages
- [ ] Slow network handled
- [ ] Retry mechanisms work (if any)

### 9.2 Authentication Errors
- [ ] Invalid OAuth credentials handled
- [ ] Expired tokens refresh
- [ ] OAuth callback errors handled
- [ ] "Already redeemed" error handled

### 9.3 Data Edge Cases
- [ ] Empty calendars handled
- [ ] Large number of events (100+)
- [ ] Events in different timezones
- [ ] All-day events work
- [ ] Recurring events work
- [ ] Special characters in titles
- [ ] Very long event titles

### 9.4 Database Edge Cases
- [ ] Duplicate events handled
- [ ] Data integrity maintained
- [ ] Missing user associations handled

**Notes:**
```
[Add any issues or observations here]
```

---

## 10. Performance

### 10.1 Load Testing
- [ ] 100+ events render smoothly
- [ ] Sync performance acceptable
- [ ] Conflict detection fast
- [ ] Free slots calculation fast

### 10.2 Response Times
- [ ] Sync operation: _____ seconds
- [ ] Calendar load: _____ seconds
- [ ] API response: _____ seconds

### 10.3 Memory Usage
- [ ] Browser memory usage acceptable
- [ ] No memory leaks observed
- [ ] Proper cleanup on navigation

**Notes:**
```
[Add any issues or observations here]
```

---

## 11. Security

### 11.1 Authentication Security
- [ ] Tokens stored securely
- [ ] Token refresh works
- [ ] Session timeout works
- [ ] CORS configured correctly

### 11.2 Data Security
- [ ] User data isolated
- [ ] Unauthorized access prevented
- [ ] Input sanitization works

**Notes:**
```
[Add any issues or observations here]
```

---

## 12. Integration Testing

### 12.1 End-to-End User Flows
- [ ] Flow 1: New user → Google login → Sync → View calendar → Check conflicts
- [ ] Flow 2: Existing user → Add Microsoft → Sync all → Bidirectional sync → View summary
- [ ] Flow 3: Multi-account user → Sync → Find free slots → Schedule meeting
- [ ] Flow 4: User with conflicts → View conflicts → Resolve → Re-sync

### 12.2 Cross-Feature Integration
- [ ] Sync updates calendar view
- [ ] Conflicts update after sync
- [ ] Free slots consider all synced events
- [ ] Summary reflects all changes

**Notes:**
```
[Add any issues or observations here]
```

---

## 13. Pre-Presentation Checklist

### 13.1 Final Verification
- [ ] All critical features working
- [ ] No console errors in browser
- [ ] No backend errors in logs
- [ ] Database queries optimized
- [ ] All test accounts ready
- [ ] Demo data prepared

### 13.2 Presentation Preparation
- [ ] Demo script prepared
- [ ] Test scenarios for demo ready
- [ ] Backup plan if live demo fails
- [ ] Tested on presentation device
- [ ] Internet connection stable
- [ ] Screenshots/videos as backup

### 13.3 Documentation
- [ ] README up-to-date
- [ ] API documentation current
- [ ] Known issues documented
- [ ] Setup instructions verified

---

## Issues Found

### Critical Issues
```
[List critical issues that must be fixed]
```

### Important Issues
```
[List important issues that should be fixed]
```

### Minor Issues
```
[List minor issues that can be fixed later]
```

---

## Test Completion Summary

**Date:** ________________  
**Tester:** ________________  
**Total Tests:** _____  
**Passed:** _____  
**Failed:** _____  
**Notes:** ________________

