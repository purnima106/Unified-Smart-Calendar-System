import { useState, useEffect, useRef } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import listPlugin from '@fullcalendar/list';
import { Video } from 'lucide-react';
import { calendarAPI } from '../services/api';
import LoadingSpinner from './LoadingSpinner';

// Use the same logic as our API service:
// - Prefer VITE_API_URL when set (Docker / production)
// - Fallback to local backend in dev
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const CalendarView = ({ user, connections }) => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState('');
  const [view, setView] = useState('dayGridMonth');
  const [debugInfo, setDebugInfo] = useState({});
  const calendarRef = useRef(null);

  useEffect(() => {
    console.log('CalendarView mounted');
    loadEvents();
  }, []);

  const loadEvents = async () => {
    try {
      setLoading(true);
      setError('');
      
      console.log('Loading events for user:', user?.id);
      
      // Get events from today onwards (exclude past events)
      const now = new Date();
      now.setHours(0, 0, 0, 0); // Start of today
      const startDate = now; // Start from today
      const endDate = new Date('2025-12-31T23:59:59Z');   // End at December 2025
      
      console.log('Date range:', { startDate: startDate.toISOString(), endDate: endDate.toISOString() });
      
      // First, test the backend connection
      try {
        const testResponse = await fetch(`${API_BASE_URL}/calendar/test`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        if (testResponse.ok) {
          const testData = await testResponse.json();
          console.log('Backend test successful:', testData);
          setDebugInfo(prev => ({ ...prev, backendTest: testData }));
        } else {
          console.warn('Backend test failed:', testResponse.status);
        }
      } catch (testError) {
        console.error('Backend connection test failed:', testError);
        setError(`Cannot connect to backend server. Please make sure the Flask server is running on ${API_BASE_URL}`);
        setLoading(false);
        return;
      }
      
      // Load events using the API service (includes credentials for authentication)
      const params = {
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
        _t: new Date().getTime() // Cache busting
      };
      
      const response = await calendarAPI.getEvents(params);
      const data = response.data;
      console.log('API response:', data);
      
      setDebugInfo(prev => ({ 
        ...prev, 
        apiResponse: data,
        timestamp: new Date().toISOString()
      }));
      
      if (!data.events || !Array.isArray(data.events)) {
        console.warn('No events array in response:', data);
        setEvents([]);
        setLoading(false);
        return;
      }
      
      console.log(`Processing ${data.events.length} events from API`);
      
      const formattedEvents = data.events.map(event => {
        // Ensure proper date formatting
        let startDate, endDate;
        
        try {
          startDate = new Date(event.start_time);
          endDate = new Date(event.end_time);
          
          // Validate dates
          if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
            console.warn('Invalid date in event:', event);
            return null;
          }
          
          // Filter out past events (events that have already ended)
          const now = new Date();
          if (endDate < now) {
            console.log(`Filtering out past event: ${event.title} (ended at ${endDate.toISOString()})`);
            return null;
          }
          
          // Debug timezone information
          console.log(`Event: ${event.title} (${event.provider})`);
          console.log(`  Organizer: ${event.organizer || 'NOT SET'}`);
          console.log(`  Original start: ${event.start_time}`);
          console.log(`  Parsed start: ${startDate.toISOString()}`);
          console.log(`  Local start: ${startDate.toLocaleString()}`);
          console.log(`  Original end: ${event.end_time}`);
          console.log(`  Parsed end: ${endDate.toISOString()}`);
          console.log(`  Local end: ${endDate.toLocaleString()}`);
          console.log(`  Has conflict: ${event.has_conflict}`);
          console.log(`  User ID: ${event.user_id}`);
          
        } catch (dateError) {
          console.error('Date parsing error for event:', event, dateError);
          return null;
        }
        
        // Include account email in title - try organizer first, then extract from provider_event_id
        let eventTitle = event.title || 'Untitled Event';
        let accountEmail = null;
        
        // First try organizer field
        if (event.organizer && typeof event.organizer === 'string' && event.organizer.includes('@')) {
          accountEmail = event.organizer.trim();
          console.log(`Found email in organizer: ${accountEmail}`);
        }
        // If organizer is missing, try to extract from provider_event_id (format: email:event_id)
        else if (event.provider_event_id && typeof event.provider_event_id === 'string') {
          // Check if it contains @ and : (format: email:event_id)
          if (event.provider_event_id.includes('@') && event.provider_event_id.includes(':')) {
            const parts = event.provider_event_id.split(':');
            if (parts.length >= 2 && parts[0].includes('@')) {
              accountEmail = parts[0].trim();
              console.log(`Extracted email from provider_event_id: ${accountEmail}`);
            }
          }
        }
        
        // Always show account email in title if found
        if (accountEmail) {
          // Show account email in title (e.g., "Meeting [user@gmail.com]")
          eventTitle = `${eventTitle} [${accountEmail}]`;
          console.log(`✅ Added email to title: "${eventTitle}"`);
        } else {
          console.warn(`⚠️ Event "${event.title}" has no account email.`, {
            organizer: event.organizer,
            provider_event_id: event.provider_event_id,
            fullEvent: event
          });
        }
        
        return {
          id: event.id,
          title: eventTitle,
          start: startDate.toISOString(),
          end: endDate.toISOString(),
          allDay: event.all_day || false,
          backgroundColor: getEventColor(event),
          borderColor: getEventBorderColor(event),
          textColor: '#ffffff',
            extendedProps: {
            provider: event.provider || 'unknown',
            hasConflict: event.has_conflict || false,
            location: event.location || '',
            description: event.description || '',
            attendees: event.attendees || [],
            organizer: event.organizer || '',
            accountEmail: accountEmail || '', // Store account email for easy access
            userId: event.user_id,
            originalTitle: event.title || 'Untitled Event', // Keep original title
            meetLink: event.meet_link || null // Store meet link
          }
        };
      }).filter(event => event !== null); // Remove invalid events
      
      console.log(`Successfully formatted ${formattedEvents.length} events`);
      console.log('Formatted events:', formattedEvents);
      setEvents(formattedEvents);
      
      setDebugInfo(prev => ({ 
        ...prev, 
        formattedEvents: formattedEvents.length,
        originalEvents: data.events.length
      }));
      
    } catch (error) {
      console.error('Error loading events:', error);
      setError(`Failed to load calendar events: ${error.message}`);
      setDebugInfo(prev => ({ ...prev, error: error.message }));
    } finally {
      setLoading(false);
    }
  };

  const handleSyncAll = async () => {
    try {
      setSyncing(true);
      setError('');
      console.log('Starting sync all...');
      
      // Try using the API service first
      try {
        const response = await calendarAPI.syncAll();
        console.log('Sync completed via API service:', response.data);
        await loadEvents(); // Reload events after sync
      } catch (apiError) {
        console.warn('API service sync failed, trying direct fetch:', apiError);
        
        // Fallback to direct fetch
        const response = await fetch(`${API_BASE_URL}/calendar/sync/all`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('Sync completed via direct fetch:', data);
          await loadEvents();
        } else {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Sync failed');
        }
      }
    } catch (error) {
      console.error('Sync error:', error);
      setError(`Failed to sync calendars: ${error.message}`);
    } finally {
      setSyncing(false);
    }
  };

  const createSampleEvents = async () => {
    try {
      setSyncing(true);
      setError('');
      console.log('Creating sample events...');
      
      const response = await fetch(`${API_BASE_URL}/calendar/create-sample-events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Sample events created:', data);
        await loadEvents(); // Reload events after creating samples
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create sample events');
      }
    } catch (error) {
      console.error('Create sample events error:', error);
      setError(`Failed to create sample events: ${error.message}`);
    } finally {
      setSyncing(false);
    }
  };

  const clearEvents = async () => {
    try {
      setSyncing(true);
      setError('');
      console.log('Clearing events...');
      
      const response = await fetch(`${API_BASE_URL}/calendar/clear-events`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Events cleared:', data);
        await loadEvents(); // Reload events after clearing
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to clear events');
      }
    } catch (error) {
      console.error('Clear events error:', error);
      setError(`Failed to clear events: ${error.message}`);
    } finally {
      setSyncing(false);
    }
  };

  const clearConflicts = async () => {
    try {
      setSyncing(true);
      setError('');
      console.log('Clearing conflicts...');
      
      const response = await fetch(`${API_BASE_URL}/calendar/clear-conflicts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Conflicts cleared:', data);
        await loadEvents(); // Reload events after clearing conflicts
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to clear conflicts');
      }
    } catch (error) {
      console.error('Clear conflicts error:', error);
      setError(`Failed to clear conflicts: ${error.message}`);
    } finally {
      setSyncing(false);
    }
  };

  const handleViewOnlySync = async () => {
    try {
      setSyncing(true);
      setError('');
      console.log('Starting view-only sync...');
      
      // Try using the API service first
      try {
        const response = await calendarAPI.syncViewOnly();
        console.log('View-only sync completed via API service:', response.data);
        await loadEvents(); // Reload events after sync
      } catch (apiError) {
        console.warn('API service view-only sync failed, trying direct fetch:', apiError);
        
        // Fallback to direct fetch
        const response = await fetch(`${API_BASE_URL}/calendar/sync/view-only`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('View-only sync completed via direct fetch:', data);
          await loadEvents();
        } else {
          const errorData = await response.json();
          throw new Error(errorData.error || 'View-only sync failed');
        }
      }
    } catch (error) {
      console.error('View-only sync error:', error);
      setError(`Failed to sync for view: ${error.message}`);
    } finally {
      setSyncing(false);
    }
  };

  const handleBidirectionalSync = async () => {
    try {
      setSyncing(true);
      setError('');
      console.log('Starting bidirectional sync...');
      
      // Try using the API service first
      try {
        const response = await calendarAPI.syncBidirectional();
        console.log('Bidirectional sync completed via API service:', response.data);
        await loadEvents(); // Reload events after sync
      } catch (apiError) {
        console.warn('API service bidirectional sync failed, trying direct fetch:', apiError);
        
        // Fallback to direct fetch
        const response = await fetch(`${API_BASE_URL}/calendar/sync/bidirectional`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('Bidirectional sync completed via direct fetch:', data);
          await loadEvents();
        } else {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Bidirectional sync failed');
        }
      }
    } catch (error) {
      console.error('Bidirectional sync error:', error);
      setError(`Failed to sync bidirectionally: ${error.message}`);
    } finally {
      setSyncing(false);
    }
  };

  const getEventColor = (event) => {
    // Provider-based colors (prioritize provider over conflicts)
    const provider = event.provider?.toLowerCase();
    
    console.log(`Event "${event.title}" - Provider: ${provider}, Has Conflict: ${event.has_conflict}`);
    
    switch (provider) {
      case 'google':
        // Google events are always red (darker if conflict)
        const googleColor = event.has_conflict ? '#dc2626' : '#ef4444';
        console.log(`  -> Google event, using color: ${googleColor}`);
        return googleColor;
      case 'microsoft':
        // Microsoft events are always blue (darker if conflict)
        const microsoftColor = event.has_conflict ? '#1e40af' : '#2563eb';
        console.log(`  -> Microsoft event, using color: ${microsoftColor}`);
        return microsoftColor;
      default:
        // Default to conflict red if no provider, otherwise purple
        const defaultColor = event.has_conflict ? '#dc2626' : '#9333ea';
        console.log(`  -> Unknown provider (${provider}), using color: ${defaultColor}`);
        return defaultColor;
    }
  };

  const getEventBorderColor = (event) => {
    // Provider-based border colors (prioritize provider over conflicts)
    const provider = event.provider?.toLowerCase();
    
    switch (provider) {
      case 'google':
        // Use darker red for conflicts, normal red border for non-conflicts
        return event.has_conflict ? '#991b1b' : '#b91c1c'; // Darker Google red
      case 'microsoft':
        // Use darker blue for conflicts, normal blue border for non-conflicts
        return event.has_conflict ? '#1e3a8a' : '#1d4ed8'; // Darker Microsoft blue
      default:
        // Default to conflict red border if no provider, otherwise purple
        return event.has_conflict ? '#991b1b' : '#7e22ce'; // Darker default purple (theme color)
    }
  };

  const handleEventClick = (clickInfo) => {
    const event = clickInfo.event;
    const extendedProps = event.extendedProps;
    
    // Create event details modal content
    const startTime = event.start ? event.start.toLocaleString() : 'N/A';
    const endTime = event.end ? event.end.toLocaleString() : 'N/A';
    
    // Get account email from extendedProps or extract from organizer/provider_event_id
    let accountEmail = extendedProps.accountEmail;
    if (!accountEmail && extendedProps.organizer && extendedProps.organizer.includes('@')) {
      accountEmail = extendedProps.organizer;
    }
    
    // Check if there's a meet link
    const meetLink = extendedProps.meetLink;
    
    let details = `
Event Details:
━━━━━━━━━━━━━
Title: ${extendedProps.originalTitle || event.title}
${accountEmail ? `Gmail Account: ${accountEmail}` : ''}
Time: ${startTime} - ${endTime}
Provider: ${extendedProps.provider}
${extendedProps.location ? `Location: ${extendedProps.location}` : ''}
${extendedProps.description ? `Description: ${extendedProps.description}` : ''}
${extendedProps.hasConflict ? '⚠️ This event has conflicts!' : ''}
    `.trim();
    
    if (meetLink) {
      details += `\n\n🔗 Google Meet: ${meetLink}`;
      // Open meet link in new tab
      if (window.confirm(details + '\n\nWould you like to join the meeting?')) {
        window.open(meetLink, '_blank');
        return;
      }
    }
    
    alert(details); // In a real app, you'd use a proper modal component
  };

  const handleDateSelect = (selectInfo) => {
    const title = prompt('Please enter a title for your event');
    if (title) {
      // In a real app, you'd create the event via API
      console.log('Creating event:', {
        title,
        start: selectInfo.startStr,
        end: selectInfo.endStr,
        allDay: selectInfo.allDay
      });
    }
    selectInfo.view.calendar.unselect();
  };

  console.log('CalendarView render - loading:', loading, 'events:', events.length, 'error:', error);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
        <span className="ml-3 text-gray-600">Loading calendar...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Calendar</h1>
          <p className="text-gray-600 mt-1">
            Your unified calendar view with events from all connected calendars
          </p>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={loadEvents}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Refresh</span>
          </button>
          
          <button
            onClick={() => {
              setEvents([]); // Clear current events
              setTimeout(() => loadEvents(), 100); // Force reload after clearing
            }}
            className="px-4 py-2 border border-orange-300 rounded-md text-sm font-medium text-orange-700 bg-white hover:bg-orange-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Force Refresh</span>
          </button>
          
          <button
            onClick={handleSyncAll}
            disabled={syncing}
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 flex items-center space-x-2"
          >
            {syncing ? (
              <LoadingSpinner size="sm" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            )}
            <span>{syncing ? 'Syncing...' : 'Sync All'}</span>
          </button>
          
          <button
            onClick={handleViewOnlySync}
            disabled={syncing}
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 flex items-center space-x-2"
          >
            {syncing ? (
              <LoadingSpinner size="sm" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
            )}
            <span>{syncing ? 'Syncing...' : 'View-Only Sync'}</span>
          </button>
          
          <button
            onClick={handleBidirectionalSync}
            disabled={syncing}
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 flex items-center space-x-2"
          >
            {syncing ? (
              <LoadingSpinner size="sm" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
            )}
            <span>{syncing ? 'Syncing...' : 'Bidirectional Sync'}</span>
          </button>
          
          <button
            onClick={createSampleEvents}
            disabled={syncing}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            <span>Create Sample Events</span>
          </button>

          <button
            onClick={clearEvents}
            disabled={syncing}
            className="px-4 py-2 border border-red-300 rounded-md text-sm font-medium text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            <span>Clear Events</span>
          </button>

          <button
            onClick={clearConflicts}
            disabled={syncing}
            className="px-4 py-2 border border-yellow-300 rounded-md text-sm font-medium text-yellow-700 bg-white hover:bg-yellow-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 disabled:opacity-50 flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>Clear Conflicts</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <p className="text-red-700 text-sm mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Debug Panel - Always show in development */}
      <div className="bg-gray-50 dark:bg-gray-900 dark:text-white border border-gray-200 dark:border-gray-800 rounded-lg p-4">
        <details className="cursor-pointer">
          <summary className="font-semibold text-gray-900 dark:text-white mb-2">Debug Information</summary>
          <pre className="text-xs bg-gray-100 dark:bg-gray-800 dark:text-gray-300 p-2 rounded overflow-auto max-h-40">
            {JSON.stringify(debugInfo, null, 2)}
          </pre>
        </details>
      </div>

      {/* Calendar Legend */}
      <div className="bg-white dark:bg-black dark:text-white shadow rounded-lg p-6 border border-gray-200 dark:border-gray-800">
        <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Calendar Legend</h3>
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-red-500 rounded" style={{ backgroundColor: '#ef4444' }}></div>
            <span className="text-sm text-gray-600 dark:text-gray-300">Google Calendar</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#2563eb' }}></div>
            <span className="text-sm text-gray-600 dark:text-gray-300">Microsoft Calendar</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 bg-red-600 rounded" style={{ backgroundColor: '#dc2626' }}></div>
            <span className="text-sm text-gray-600 dark:text-gray-300">Conflicts</span>
          </div>
        </div>
      </div>

      {/* FullCalendar */}
      <div className="bg-white dark:bg-black dark:text-white shadow rounded-lg overflow-hidden border border-gray-200 dark:border-gray-800">
        <FullCalendar
          ref={calendarRef}
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin, listPlugin]}
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
          }}
          initialView={view}
          editable={true}
          selectable={true}
          selectMirror={true}
          dayMaxEvents={true}
          weekends={true}
          events={events}
          select={handleDateSelect}
          eventClick={handleEventClick}
          height="auto"
          eventDisplay="block"
          timeZone="Asia/Kolkata"
          eventTimeFormat={{
            hour: 'numeric',
            minute: '2-digit',
            meridiem: 'short'
          }}
          slotMinTime="06:00:00"
          slotMaxTime="22:00:00"
          allDaySlot={true}
          slotDuration="00:30:00"
          slotLabelInterval="01:00"
          nowIndicator={true}
          businessHours={{
            daysOfWeek: [1, 2, 3, 4, 5], // Monday - Friday
            startTime: '09:00',
            endTime: '17:00',
          }}
          dayHeaderFormat={{
            weekday: 'long'
          }}
          titleFormat={{
            month: 'long',
            year: 'numeric'
          }}
          eventClassNames={(arg) => {
            const classes = ['calendar-event'];
            if (arg.event.extendedProps.hasConflict) {
              classes.push('has-conflict');
            }
            classes.push(`provider-${arg.event.extendedProps.provider}`);
            return classes;
          }}
          eventContent={(arg) => {
            const meetLink = arg.event.extendedProps.meetLink;
            if (meetLink) {
              return {
                html: `
                  <div style="display: flex; align-items: center; gap: 4px; width: 100%;">
                    <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${arg.event.title}</span>
                    <span 
                      onclick="event.stopPropagation(); window.open('${meetLink}', '_blank');"
                      style="
                        background: #9333ea;
                        border: none;
                        border-radius: 4px;
                        padding: 2px 6px;
                        cursor: pointer;
                        color: white;
                        font-size: 10px;
                        flex-shrink: 0;
                        user-select: none;
                      "
                      title="Join Google Meet"
                    >
                      📹
                    </span>
                  </div>
                `
              };
            }
            return { html: arg.event.title };
          }}
        />
      </div>

      {/* Event Statistics */}
      {events.length > 0 && (
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-white dark:bg-black dark:text-white shadow rounded-lg p-6 border border-gray-200 dark:border-gray-800">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-300">Total Events</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{events.length}</p>
              </div>
              <svg className="w-8 h-8 text-purple-500 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
          </div>

          <div className="bg-white dark:bg-black dark:text-white shadow rounded-lg p-6 border border-gray-200 dark:border-gray-800">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-300">Google Events</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {events.filter(e => e.extendedProps.provider === 'google').length}
                </p>
              </div>
              <div className="w-8 h-8 rounded" style={{ backgroundColor: '#ef4444' }}></div>
            </div>
          </div>

          <div className="bg-white dark:bg-black dark:text-white shadow rounded-lg p-6 border border-gray-200 dark:border-gray-800">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-300">Microsoft Events</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {events.filter(e => e.extendedProps.provider === 'microsoft').length}
                </p>
              </div>
              <div className="w-8 h-8 rounded" style={{ backgroundColor: '#2563eb' }}></div>
            </div>
          </div>
        </div>
      )}

      {/* No Events Message */}
      {!loading && events.length === 0 && (
        <div className="bg-white dark:bg-black dark:text-white shadow rounded-lg p-12 text-center border border-gray-200 dark:border-gray-800">
          <svg className="w-16 h-16 text-gray-400 dark:text-gray-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            No Events Found
          </h3>
          <p className="text-gray-600 dark:text-gray-300 mb-6 max-w-md mx-auto">
            No events found in your calendar. Try creating some sample events to test the calendar functionality.
          </p>
          <div className="space-x-3">
            <button
              onClick={createSampleEvents}
              disabled={syncing}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              Create Sample Events
            </button>
            <button
              onClick={loadEvents}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Refresh Events
            </button>
          </div>
          <div className="text-sm text-gray-500 mt-4">
            <p>For debugging:</p>
            <p>• Check the browser console for error messages</p>
            <p>• Ensure Flask backend is running on {API_BASE_URL}</p>
            <p>• Check the debug panel above for more information</p>
          </div>
        </div>
      )}

      {/* Footer with helpful information */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <svg className="w-5 h-5 text-blue-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">Development Mode</h3>
            <div className="mt-2 text-sm text-blue-700">
              <p>This calendar is running in development mode with sample data.</p>
              <p>• Click events to see details</p>
              <p>• Use "Create Sample Events" to populate the calendar</p>
              <p>• Backend connection: {debugInfo.backendTest ? '✅ Connected' : '❌ Disconnected'}</p>
              <p>• Events loaded: {events.length}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CalendarView;