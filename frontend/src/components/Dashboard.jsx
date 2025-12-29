import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Calendar, 
  RefreshCw, 
  AlertTriangle, 
  Clock, 
  BarChart3, 
  CheckCircle, 
  XCircle,
  Plus,
  ExternalLink,
  CalendarPlus,
  Trash2,
  Power,
  TrendingUp,
  FileText,
  Edit2,
  X
} from 'lucide-react';
import { calendarAPI, authAPI, availabilityAPI } from '../services/api';
import LoadingSpinner from './LoadingSpinner';

const API_BASE_URL = import.meta.env.VITE_API_URL;

const Dashboard = ({ user, connections, onConnectionsUpdate }) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [syncAllLoading, setSyncAllLoading] = useState(false);
  const [bidirectionalLoading, setBidirectionalLoading] = useState(false);
  const [createEventLoading, setCreateEventLoading] = useState(false);
  const [error, setError] = useState('');
  const [allConnections, setAllConnections] = useState([]);
  const [connectionsLoading, setConnectionsLoading] = useState(false);
  const [notes, setNotes] = useState([]);
  const [newNote, setNewNote] = useState('');
  const [editingNoteId, setEditingNoteId] = useState(null);
  const [editingNoteText, setEditingNoteText] = useState('');

  // Availability settings (owner)
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [availabilitySaving, setAvailabilitySaving] = useState(false);
  const [availability, setAvailability] = useState([]); // [{day_of_week, start_time, end_time}]
  const [defaultSlotDuration, setDefaultSlotDuration] = useState(30);

  useEffect(() => {
    if (user) {
      loadSummary();
      loadConnections();
      loadNotes();
      loadAvailability();
    }
  }, [user]);

  const loadAvailability = async () => {
    try {
      setAvailabilityLoading(true);
      const res = await availabilityAPI.getMine();
      const data = res.data || {};
      setAvailability(Array.isArray(data.availability) ? data.availability : []);
      setDefaultSlotDuration(data.default_slot_duration_minutes || 30);
    } catch (e) {
      // Don't block dashboard if availability isn't configured yet
      console.warn('Availability not loaded:', e?.response?.data || e.message);
    } finally {
      setAvailabilityLoading(false);
    }
  };

  const saveAvailability = async () => {
    try {
      setAvailabilitySaving(true);
      setError('');

      const payload = {
        default_slot_duration_minutes: defaultSlotDuration,
        availability: availability
          .filter((a) => a && a.start_time && a.end_time)
          .map((a) => ({
            day_of_week: a.day_of_week,
            start_time: a.start_time,
            end_time: a.end_time,
          })),
      };

      const res = await availabilityAPI.setMine(payload);
      const data = res.data || {};
      setAvailability(Array.isArray(data.availability) ? data.availability : []);
      setDefaultSlotDuration(data.default_slot_duration_minutes || 30);
    } catch (e) {
      setError(e?.response?.data?.error || e.message || 'Failed to save availability');
    } finally {
      setAvailabilitySaving(false);
    }
  };

  const toggleDay = (day) => {
    const existing = availability.find((a) => a.day_of_week === day);
    if (existing) {
      setAvailability(availability.filter((a) => a.day_of_week !== day));
    } else {
      setAvailability([...availability, { day_of_week: day, start_time: '10:00', end_time: '18:00' }]);
    }
  };

  const setDayTime = (day, field, value) => {
    setAvailability(
      availability.map((a) => (a.day_of_week === day ? { ...a, [field]: value } : a))
    );
  };

  const publicUsername = user?.public_username || user?.email?.split('@')?.[0];
  const publicLink = `${window.location.origin}/book/${publicUsername}`;

  // Load notes from localStorage
  const loadNotes = () => {
    try {
      const savedNotes = localStorage.getItem('calendarNotes');
      if (savedNotes) {
        setNotes(JSON.parse(savedNotes));
      }
    } catch (error) {
      console.error('Error loading notes:', error);
    }
  };

  // Save notes to localStorage
  const saveNotes = (notesToSave) => {
    try {
      localStorage.setItem('calendarNotes', JSON.stringify(notesToSave));
      setNotes(notesToSave);
    } catch (error) {
      console.error('Error saving notes:', error);
    }
  };

  const handleAddNote = () => {
    if (newNote.trim()) {
      const note = {
        id: Date.now(),
        text: newNote.trim(),
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
      const updatedNotes = [...notes, note];
      saveNotes(updatedNotes);
      setNewNote('');
    }
  };

  const handleEditNote = (noteId) => {
    const note = notes.find(n => n.id === noteId);
    if (note) {
      setEditingNoteId(noteId);
      setEditingNoteText(note.text);
    }
  };

  const handleSaveEdit = () => {
    if (editingNoteText.trim() && editingNoteId) {
      const updatedNotes = notes.map(note =>
        note.id === editingNoteId
          ? { ...note, text: editingNoteText.trim(), updatedAt: new Date().toISOString() }
          : note
      );
      saveNotes(updatedNotes);
      setEditingNoteId(null);
      setEditingNoteText('');
    }
  };

  const handleDeleteNote = (noteId) => {
    const updatedNotes = notes.filter(note => note.id !== noteId);
    saveNotes(updatedNotes);
  };

  const loadConnections = async () => {
    try {
      setConnectionsLoading(true);
      const response = await authAPI.listAllConnections();
      setAllConnections(response.data.connections || []);
    } catch (error) {
      // Silently handle 401 errors (user not authenticated)
      if (error.response?.status !== 401) {
        console.error('Error loading connections:', error);
      }
    } finally {
      setConnectionsLoading(false);
    }
  };

  const handleAddGoogleAccount = async () => {
    try {
      const response = await authAPI.googleLogin();
      window.location.href = response.data.auth_url;
    } catch (error) {
      console.error('Error adding Google account:', error);
      setError('Failed to add Google account. Please try again.');
    }
  };

  const handleAddMicrosoftAccount = async () => {
    try {
      const response = await authAPI.microsoftLogin();
      window.location.href = response.data.auth_url;
    } catch (error) {
      console.error('Error adding Microsoft account:', error);
      setError('Failed to add Microsoft account. Please try again.');
    }
  };

  const handleRemoveConnection = async (connectionId, accountEmail) => {
    if (!window.confirm(`Are you sure you want to remove ${accountEmail}?`)) {
      return;
    }
    
    try {
      await authAPI.removeConnection(connectionId);
      await loadConnections();
      await onConnectionsUpdate();
      await loadSummary();
    } catch (error) {
      console.error('Error removing connection:', error);
      setError('Failed to remove account. Please try again.');
    }
  };

  const loadSummary = async () => {
    try {
      setLoading(true);
      const response = await calendarAPI.getSummary();
      setSummary(response.data);
    } catch (error) {
      console.error('Error loading summary:', error);
      setError('Failed to load calendar summary');
    } finally {
      setLoading(false);
    }
  };

  const handleSyncAll = async () => {
    try {
      setSyncAllLoading(true);
      setError('');
      await calendarAPI.syncAll();
      await loadSummary();
      await onConnectionsUpdate();
    } catch (error) {
      console.error('Sync error:', error);
      setError('Failed to sync calendars. Please try again.');
    } finally {
      setSyncAllLoading(false);
    }
  };

  const handleBidirectionalSync = async () => {
    try {
      setBidirectionalLoading(true);
      setError('');
      console.log('Starting bidirectional sync from Dashboard (NO notifications - just mirroring existing events)...');
      
      // Try using the API service first
      try {
        const response = await calendarAPI.syncBidirectional();
        console.log('Bidirectional sync completed via API service:', response.data);
        await loadSummary();
        await onConnectionsUpdate();
      } catch (apiError) {
        console.warn('API service bidirectional sync failed, trying direct fetch:', apiError);
        
        // Fallback to direct fetch
        const response = await fetch(`${API_BASE_URL}/calendar/sync/bidirectional`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('Bidirectional sync completed via direct fetch:', data);
          await loadSummary();
          await onConnectionsUpdate();
        } else {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Bidirectional sync failed');
        }
      }
    } catch (error) {
      console.error('Bidirectional sync error:', error);
      setError(`Failed to sync bidirectionally: ${error.message}`);
    } finally {
      setBidirectionalLoading(false);
    }
  };



  const handleCreateEvent = async () => {
    try {
      setCreateEventLoading(true);
      setError('');
      console.log('Creating NEW event with notifications...');
      
      // Sample event data for testing
      const eventData = {
        title: 'New Team Meeting',
        description: 'This is a NEW event created through the app - participants will receive notifications',
        location: 'Conference Room A',
        start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(), // Tomorrow
        end_time: new Date(Date.now() + 24 * 60 * 60 * 1000 + 60 * 60 * 1000).toISOString(), // Tomorrow + 1 hour
        all_day: false,
        attendees: [
          { email: 'colleague1@example.com', name: 'John Doe' },
          { email: 'colleague2@example.com', name: 'Jane Smith' }
        ],
        target_calendar: 'both' // Create in both Google and Microsoft
      };
      
      // Try using the API service first
      try {
        const response = await calendarAPI.createEvent(eventData);
        console.log('Event creation completed via API service:', response.data);
        await loadSummary();
        await onConnectionsUpdate();
        setError(''); // Clear any previous errors
      } catch (apiError) {
        console.warn('API service event creation failed, trying direct fetch:', apiError);
        
        // Fallback to direct fetch
        const response = await fetch(`${API_BASE_URL}/calendar/create-event`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(eventData)
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('Event creation completed via direct fetch:', data);
          await loadSummary();
          await onConnectionsUpdate();
          setError(''); // Clear any previous errors
        } else {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Event creation failed');
        }
      }
    } catch (error) {
      console.error('Event creation error:', error);
      setError(`Failed to create event: ${error.message}`);
    } finally {
      setCreateEventLoading(false);
    }
  };

  const quickActions = [
    {
      title: 'Create Event',
      description: 'Create NEW event with notifications to participants',
      icon: CalendarPlus,
      action: handleCreateEvent,
      color: 'bg-green-500'
    },
    {
      title: 'View Calendar',
      description: 'See all your events in one unified view',
      icon: Calendar,
      link: '/calendar',
      color: 'bg-purple-500'
    },

    {
      title: 'Bidirectional Sync',
      description: 'Mirror existing events between calendars (NO notifications sent)',
      icon: RefreshCw,
      action: handleBidirectionalSync,
      color: 'bg-purple-500'
    },
    {
      title: 'Check Conflicts',
      description: 'Identify overlapping meetings',
      icon: AlertTriangle,
      link: '/conflicts',
      color: 'bg-purple-500'
    },
    {
      title: 'Find Free Slots',
      description: 'Discover available meeting times',
      icon: Clock,
      link: '/free-slots',
      color: 'bg-purple-500'
    },
    {
      title: 'View Summary',
      description: 'See calendar analytics and insights',
      icon: BarChart3,
      link: '/summary',
      color: 'bg-purple-500'
    }
  ];

  // Build connection status from all connections
  const googleAccounts = allConnections.filter(c => c.provider === 'google' && c.is_active);
  const microsoftAccounts = allConnections.filter(c => c.provider === 'microsoft' && c.is_active);
  
  const connectionStatus = [
    ...googleAccounts.map(conn => ({
      id: conn.id,
      name: conn.provider_account_name || conn.provider_account_email,
      email: conn.provider_account_email,
      connected: conn.is_connected,
      color: 'google',
      icon: 'G',
      provider: 'google',
      last_synced: conn.last_synced
    })),
    ...microsoftAccounts.map(conn => ({
      id: conn.id,
      name: conn.provider_account_name || conn.provider_account_email,
      email: conn.provider_account_email,
      connected: conn.is_connected,
      color: 'microsoft',
      icon: 'M',
      provider: 'microsoft',
      last_synced: conn.last_synced
    }))
  ];

  // If no connections found, show legacy status
  if (connectionStatus.length === 0 && connections?.google?.connected) {
    connectionStatus.push({
      name: 'Google Calendar',
      connected: connections.google.connected,
      color: 'google',
      icon: 'G'
    });
  }

  return (
    <div className="space-y-8 pb-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">Dashboard</h1>
          <p className="text-gray-600 dark:text-white text-lg">
            Welcome back, <span className="font-semibold text-purple-600 dark:text-purple-400">{user.name}</span>! Here's your calendar overview.
          </p>
        </div>
        
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleSyncAll}
            disabled={syncAllLoading || bidirectionalLoading || createEventLoading || !user.has_connected_calendars}
            className="btn-primary flex items-center space-x-2 shadow-md hover:shadow-lg"
          >
            {syncAllLoading ? (
              <LoadingSpinner size="sm" />
            ) : (
              <RefreshCw className={`w-4 h-4 ${syncAllLoading ? 'animate-spin' : ''}`} />
            )}
            <span>{syncAllLoading ? 'Syncing...' : 'Sync All'}</span>
          </button>
          
          <button
            onClick={handleBidirectionalSync}
            disabled={syncAllLoading || bidirectionalLoading || createEventLoading || !user.has_connected_calendars}
            className="btn-secondary flex items-center space-x-2 shadow-sm hover:shadow-md"
          >
            {bidirectionalLoading ? (
              <LoadingSpinner size="sm" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
            )}
            <span>{bidirectionalLoading ? 'Syncing...' : 'Bidirectional Sync'}</span>
          </button>
          
          <button
            onClick={handleCreateEvent}
            disabled={syncAllLoading || bidirectionalLoading || createEventLoading || !user.has_connected_calendars}
            className="btn-primary flex items-center space-x-2 shadow-md hover:shadow-lg"
          >
            {createEventLoading ? (
              <LoadingSpinner size="sm" />
            ) : (
              <CalendarPlus className="w-4 h-4" />
            )}
            <span>{createEventLoading ? 'Creating...' : 'Create Event'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-purple-50 dark:bg-purple-900/30 border-l-4 border-purple-500 dark:border-purple-400 rounded-lg p-4 shadow-sm">
          <div className="flex items-start">
            <AlertTriangle className="w-5 h-5 text-purple-600 dark:text-purple-400 mt-0.5 flex-shrink-0" />
            <p className="text-purple-800 dark:text-purple-200 text-sm ml-3">{error}</p>
          </div>
        </div>
      )}

      {/* Sync Information */}
      <div className="bg-gradient-to-r from-purple-50 to-purple-100 dark:from-purple-900/30 dark:to-purple-800/30 border border-purple-200 dark:border-purple-800 rounded-2xl p-6 shadow-md">
        <div className="flex items-start">
          <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 dark:from-purple-600 dark:to-purple-700 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="ml-5 flex-1">
            <h3 className="text-lg font-bold text-purple-900 dark:text-purple-200 mb-3">Sync Options</h3>
            <div className="space-y-2.5 text-sm text-purple-800 dark:text-purple-300">
              <div className="flex items-start">
                <span className="font-bold mr-2">•</span>
                <p><span className="font-semibold">Create Event:</span> Create NEW events with notifications sent to participants</p>
              </div>
              <div className="flex items-start">
                <span className="font-bold mr-2">•</span>
                <p><span className="font-semibold">Sync All:</span> Fetches events from your connected calendars to the unified view</p>
              </div>
              <div className="flex items-start">
                <span className="font-bold mr-2">•</span>
                <p><span className="font-semibold">Bidirectional Sync:</span> Mirrors existing events between calendars (NO notifications sent - this is just for visibility)</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Connection Status */}
      <div className="space-y-6">
        <div className="flex items-center justify-between section-header">
          <div>
            <h2 className="section-title dark:text-white">Connected Accounts</h2>
            <p className="section-subtitle dark:text-white">Manage your calendar connections</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleAddGoogleAccount}
              className="btn-google flex items-center space-x-2 shadow-md hover:shadow-lg"
            >
              <Plus className="w-4 h-4" />
              <span>Add Google Account</span>
            </button>
            <button
              onClick={handleAddMicrosoftAccount}
              className="btn-microsoft flex items-center space-x-2 shadow-md hover:shadow-lg"
            >
              <Plus className="w-4 h-4" />
              <span>Add Microsoft Account</span>
            </button>
          </div>
        </div>
        
        {connectionsLoading ? (
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner size="lg" />
          </div>
        ) : connectionStatus.length > 0 ? (
          <div className="grid md:grid-cols-2 gap-4">
            {connectionStatus.map((connection) => (
              <div key={connection.id || connection.name} className="card-hover group relative overflow-hidden">
                {/* Connection status indicator bar */}
                {connection.connected && (
                  <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 to-purple-600"></div>
                )}
                <div className="flex items-center justify-between pt-1">
                  <div className="flex items-center space-x-4 flex-1">
                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-white font-bold shadow-lg transition-all duration-300 group-hover:scale-110 group-hover:shadow-xl ${
                      connection.connected 
                        ? 'bg-gradient-to-br from-purple-500 to-purple-600'
                        : 'bg-gray-300 dark:bg-gray-700'
                    }`}>
                      <span className="text-lg">{connection.icon}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-bold text-gray-900 dark:text-white text-base mb-1">
                        {connection.name}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-300 truncate">
                        {connection.email || connection.name}
                      </p>
                      {connection.last_synced && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5">
                          Last synced: {new Date(connection.last_synced).toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    {connection.connected ? (
                      <div className="flex items-center space-x-2 px-3 py-1.5 bg-purple-50 dark:bg-purple-900/30 rounded-lg">
                        <CheckCircle className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                        <span className="text-xs font-semibold text-purple-600 dark:text-purple-400 hidden sm:inline">Connected</span>
                      </div>
                    ) : (
                      <div className="px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg">
                        <XCircle className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                      </div>
                    )}
                    {connection.id && (
                      <button
                        onClick={() => handleRemoveConnection(connection.id, connection.email || connection.name)}
                        className="p-2.5 text-gray-400 dark:text-gray-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-all duration-200"
                        title="Remove account"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card-elevated text-center py-12">
            <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Calendar className="w-8 h-8 text-purple-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
              No Accounts Connected
            </h3>
            <p className="text-gray-600 dark:text-white mb-6 max-w-md mx-auto">
              Connect your Google Calendar or Microsoft Outlook to start syncing events and managing your schedule
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                onClick={handleAddGoogleAccount}
                className="btn-google flex items-center space-x-2"
              >
                <Plus className="w-4 h-4" />
                <span>Add Google Account</span>
              </button>
              <button
                onClick={handleAddMicrosoftAccount}
                className="btn-microsoft flex items-center space-x-2"
              >
                <Plus className="w-4 h-4" />
                <span>Add Microsoft Account</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Availability Settings (New Feature) */}
      <div className="space-y-4">
        <div className="section-header">
          <div>
            <h2 className="section-title dark:text-white">Availability</h2>
            <p className="section-subtitle dark:text-white">
              Configure your public booking availability (Calendly-style). Clients see only available slots.
            </p>
          </div>
        </div>

        <div className="card-hover">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div className="space-y-1">
              <div className="text-sm font-semibold text-gray-900 dark:text-white">Public booking link</div>
              <div className="text-sm text-gray-600 dark:text-gray-300 break-all">
                {publicLink}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Share this link with clients. No login required.
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => navigator.clipboard.writeText(publicLink)}
                className="btn-secondary"
              >
                Copy link
              </button>
              <Link to={`/book/${publicUsername}`} className="btn-primary">
                Preview booking page
              </Link>
            </div>
          </div>

          <div className="mt-6 grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1 space-y-3">
              <div className="text-sm font-semibold text-gray-900 dark:text-white">Default slot duration</div>
              <div className="flex gap-2">
                {[30, 60].map((d) => (
                  <button
                    key={d}
                    onClick={() => setDefaultSlotDuration(d)}
                    className={`px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
                      defaultSlotDuration === d
                        ? 'bg-purple-600 text-white'
                        : 'bg-purple-50 text-purple-700 hover:bg-purple-100'
                    }`}
                  >
                    {d} min
                  </button>
                ))}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Clients can still switch between 30/60 minutes on the public page.
              </div>
            </div>

            <div className="lg:col-span-2 space-y-3">
              <div className="text-sm font-semibold text-gray-900 dark:text-white">Working days</div>
              {availabilityLoading ? (
                <div className="flex items-center gap-3 py-6">
                  <LoadingSpinner size="sm" />
                  <span className="text-sm text-gray-600 dark:text-gray-300">Loading availability…</span>
                </div>
              ) : (
                <div className="space-y-3">
                  {[
                    { day: 0, label: 'Mon' },
                    { day: 1, label: 'Tue' },
                    { day: 2, label: 'Wed' },
                    { day: 3, label: 'Thu' },
                    { day: 4, label: 'Fri' },
                    { day: 5, label: 'Sat' },
                    { day: 6, label: 'Sun' },
                  ].map(({ day, label }) => {
                    const enabled = availability.some((a) => a.day_of_week === day);
                    const item = availability.find((a) => a.day_of_week === day);
                    return (
                      <div key={day} className="flex flex-col md:flex-row md:items-center gap-3 p-3 rounded-xl border border-gray-200 dark:border-gray-800">
                        <button
                          onClick={() => toggleDay(day)}
                          className={`px-3 py-2 rounded-lg text-sm font-semibold ${
                            enabled ? 'bg-purple-600 text-white' : 'bg-gray-100 dark:bg-gray-900 text-gray-700 dark:text-gray-300'
                          }`}
                        >
                          {label}
                        </button>

                        {enabled ? (
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm text-gray-600 dark:text-gray-300">From</span>
                            <input
                              type="time"
                              value={item?.start_time || '10:00'}
                              onChange={(e) => setDayTime(day, 'start_time', e.target.value)}
                              className="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-black text-gray-900 dark:text-white"
                            />
                            <span className="text-sm text-gray-600 dark:text-gray-300">to</span>
                            <input
                              type="time"
                              value={item?.end_time || '18:00'}
                              onChange={(e) => setDayTime(day, 'end_time', e.target.value)}
                              className="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-black text-gray-900 dark:text-white"
                            />
                          </div>
                        ) : (
                          <span className="text-sm text-gray-500 dark:text-gray-400">Not available</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              <div className="flex justify-end">
                <button
                  onClick={saveAvailability}
                  disabled={availabilitySaving}
                  className="btn-primary"
                >
                  {availabilitySaving ? 'Saving…' : 'Save availability'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <div className="section-header mb-6">
          <h2 className="section-title dark:text-white">Quick Actions</h2>
          <p className="section-subtitle dark:text-white">Access your calendar tools and features</p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {quickActions.map((action) => {
            const Icon = action.icon;
            
            if (action.action) {
              // Action button
              return (
                <button
                  key={action.title}
                  onClick={action.action}
                  disabled={syncAllLoading || bidirectionalLoading || createEventLoading}
                  className="card-hover group text-left w-full relative overflow-hidden"
                >
                  {/* Hover gradient effect */}
                  <div className="absolute inset-0 bg-gradient-to-br from-purple-50/0 to-purple-50/0 dark:from-purple-900/0 dark:to-purple-900/0 group-hover:from-purple-50/50 group-hover:to-purple-100/30 dark:group-hover:from-purple-900/20 dark:group-hover:to-purple-800/10 transition-all duration-300"></div>
                  
                  <div className="relative flex items-start space-x-4">
                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-white shadow-lg transition-all duration-300 group-hover:scale-110 group-hover:shadow-xl ${action.color.replace('bg-green-500', 'bg-gradient-to-br from-purple-500 to-purple-600').replace('bg-purple-500', 'bg-gradient-to-br from-purple-500 to-purple-600')}`}>
                      <Icon className="w-7 h-7" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-bold text-gray-900 dark:text-white group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors mb-1.5 text-base">
                        {action.title}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">{action.description}</p>
                    </div>
                    <svg className="w-5 h-5 text-gray-400 dark:text-gray-500 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors flex-shrink-0 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                    </svg>
                  </div>
                </button>
              );
            } else {
              // Link
              return (
                <Link
                  key={action.title}
                  to={action.link}
                  className="card-hover group relative overflow-hidden"
                >
                  {/* Hover gradient effect */}
                  <div className="absolute inset-0 bg-gradient-to-br from-purple-50/0 to-purple-50/0 dark:from-purple-900/0 dark:to-purple-900/0 group-hover:from-purple-50/50 group-hover:to-purple-100/30 dark:group-hover:from-purple-900/20 dark:group-hover:to-purple-800/10 transition-all duration-300"></div>
                  
                  <div className="relative flex items-start space-x-4">
                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-white shadow-lg transition-all duration-300 group-hover:scale-110 group-hover:shadow-xl ${action.color.replace('bg-purple-500', 'bg-gradient-to-br from-purple-500 to-purple-600')}`}>
                      <Icon className="w-7 h-7" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-bold text-gray-900 dark:text-white group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors mb-1.5 text-base">
                        {action.title}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">{action.description}</p>
                    </div>
                    <ExternalLink className="w-5 h-5 text-gray-400 dark:text-gray-500 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors flex-shrink-0 mt-1" />
                  </div>
                </Link>
              );
            }
          })}
        </div>
      </div>

      {/* Analytics & Graphs Section */}
      {summary && (
        <div>
          <div className="section-header mb-6">
            <h2 className="section-title dark:text-white">Analytics & Insights</h2>
            <p className="section-subtitle dark:text-white">Visual representation of your calendar data</p>
          </div>
          
          <div className="grid md:grid-cols-2 gap-6">
            {/* Events Distribution Chart */}
            <div className="card-hover">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
                  <BarChart3 className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 dark:text-white text-lg">Events Distribution</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-300">By calendar provider</p>
                </div>
              </div>
              <div className="space-y-4">
                {summary.total_events > 0 ? (
                  <>
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Google Calendar</span>
                        <span className="text-sm font-bold text-gray-900 dark:text-white">
                          {summary.google_events} ({summary.total_events > 0 ? ((summary.google_events / summary.total_events) * 100).toFixed(0) : 0}%)
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4 overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-purple-500 to-purple-600 h-4 rounded-full transition-all duration-500 shadow-sm"
                          style={{ width: `${summary.total_events > 0 ? (summary.google_events / summary.total_events) * 100 : 0}%` }}
                        ></div>
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Microsoft Calendar</span>
                        <span className="text-sm font-bold text-gray-900 dark:text-white">
                          {summary.microsoft_events} ({summary.total_events > 0 ? ((summary.microsoft_events / summary.total_events) * 100).toFixed(0) : 0}%)
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4 overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-purple-500 to-purple-600 h-4 rounded-full transition-all duration-500 shadow-sm"
                          style={{ width: `${summary.total_events > 0 ? (summary.microsoft_events / summary.total_events) * 100 : 0}%` }}
                        ></div>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    <BarChart3 className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>No events to display</p>
                  </div>
                )}
              </div>
            </div>

            {/* Meeting Hours Trend */}
            <div className="card-hover">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 dark:text-white text-lg">Meeting Hours</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-300">Weekly breakdown</p>
                </div>
              </div>
              <div className="space-y-3">
                {summary.total_meeting_hours > 0 ? (
                  <div className="flex items-end justify-between h-32 space-x-2">
                    {[1, 2, 3, 4, 5, 6, 7].map((day) => {
                      // Simulate weekly data (in real app, this would come from API)
                      const height = Math.random() * 80 + 20;
                      return (
                        <div key={day} className="flex-1 flex flex-col items-center">
                          <div
                            className="w-full bg-gradient-to-t from-purple-500 to-purple-600 rounded-t-lg transition-all duration-500 hover:opacity-80 cursor-pointer"
                            style={{ height: `${height}%` }}
                            title={`Day ${day}: ${(summary.total_meeting_hours / 7).toFixed(1)}h`}
                          ></div>
                          <span className="text-xs text-gray-500 dark:text-gray-400 mt-1">D{day}</span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    <TrendingUp className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>No meeting hours to display</p>
                  </div>
                )}
                <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-300">Total Hours</span>
                    <span className="text-lg font-bold text-purple-600 dark:text-purple-400">
                      {summary.total_meeting_hours.toFixed(1)}h
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Conflict Rate Visualization */}
            <div className="card-hover">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 dark:text-white text-lg">Conflict Analysis</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-300">Conflict rate overview</p>
                </div>
              </div>
              <div className="space-y-4">
                <div className="flex items-center justify-center">
                  <div className="relative w-32 h-32">
                    <svg className="transform -rotate-90 w-32 h-32">
                      <circle
                        cx="64"
                        cy="64"
                        r="56"
                        stroke="currentColor"
                        strokeWidth="12"
                        fill="none"
                        className="text-gray-200 dark:text-gray-700"
                      />
                      <circle
                        cx="64"
                        cy="64"
                        r="56"
                        stroke="currentColor"
                        strokeWidth="12"
                        fill="none"
                        strokeDasharray={`${2 * Math.PI * 56}`}
                        strokeDashoffset={`${2 * Math.PI * 56 * (1 - summary.conflict_percentage / 100)}`}
                        className="text-purple-600 dark:text-purple-400 transition-all duration-500"
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gray-900 dark:text-white">
                          {summary.conflict_percentage.toFixed(1)}%
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">Conflict Rate</div>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <span className="text-sm text-gray-600 dark:text-gray-300">Conflicts</span>
                    <span className="font-bold text-gray-900 dark:text-white">{summary.events_with_conflicts}</span>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <span className="text-sm text-gray-600 dark:text-gray-300">Total Events</span>
                    <span className="font-bold text-gray-900 dark:text-white">{summary.total_events}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Productivity Score */}
            <div className="card-hover">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
                  <BarChart3 className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 dark:text-white text-lg">Productivity Score</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-300">Calendar efficiency</p>
                </div>
              </div>
              <div className="space-y-4">
                {(() => {
                  const productivityScore = Math.max(0, Math.min(100, 100 - (summary.conflict_percentage * 2) + (summary.total_events > 0 ? 10 : 0)));
                  return (
                    <>
                      <div className="flex items-center justify-center">
                        <div className="text-5xl font-bold text-purple-600 dark:text-purple-400">
                          {productivityScore.toFixed(0)}
                        </div>
                        <span className="text-2xl text-gray-400 dark:text-gray-500 ml-1">/100</span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4 overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-purple-500 to-purple-600 h-4 rounded-full transition-all duration-500 shadow-sm"
                          style={{ width: `${productivityScore}%` }}
                        ></div>
                      </div>
                      <div className="flex items-center justify-center">
                        <span className={`px-4 py-2 rounded-lg text-sm font-semibold ${
                          productivityScore >= 80 
                            ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                            : productivityScore >= 60
                            ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                            : 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                        }`}>
                          {productivityScore >= 80 ? 'Excellent' : productivityScore >= 60 ? 'Good' : 'Needs Improvement'}
                        </span>
                      </div>
                    </>
                  );
                })()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Notes Section */}
      <div>
        <div className="section-header mb-6">
          <h2 className="section-title dark:text-white">Notes & Comments</h2>
          <p className="section-subtitle dark:text-white">Keep track of important calendar notes and reminders</p>
        </div>
        
        <div className="card-hover">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="flex-1">
              <h3 className="font-bold text-gray-900 dark:text-white text-lg mb-1">Add a Note</h3>
              <p className="text-sm text-gray-600 dark:text-gray-300">Write down important reminders or comments</p>
            </div>
          </div>
          
          <div className="flex space-x-3 mb-6">
            <textarea
              value={newNote}
              onChange={(e) => setNewNote(e.target.value)}
              placeholder="Enter your note here..."
              className="input flex-1 min-h-[100px] resize-none"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && e.ctrlKey) {
                  handleAddNote();
                }
              }}
            />
            <button
              onClick={handleAddNote}
              disabled={!newNote.trim()}
              className="btn-primary self-start disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>Add Note</span>
            </button>
          </div>
          
          {notes.length > 0 ? (
            <div className="space-y-3">
              <h4 className="font-semibold text-gray-900 dark:text-white mb-3">Your Notes ({notes.length})</h4>
              {notes.map((note) => (
                <div
                  key={note.id}
                  className="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700"
                >
                  {editingNoteId === note.id ? (
                    <div className="space-y-3">
                      <textarea
                        value={editingNoteText}
                        onChange={(e) => setEditingNoteText(e.target.value)}
                        className="input min-h-[80px] resize-none"
                        autoFocus
                      />
                      <div className="flex items-center justify-end space-x-2">
                        <button
                          onClick={() => {
                            setEditingNoteId(null);
                            setEditingNoteText('');
                          }}
                          className="btn-secondary text-sm"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleSaveEdit}
                          disabled={!editingNoteText.trim()}
                          className="btn-primary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          Save
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <p className="text-gray-900 dark:text-white mb-2 whitespace-pre-wrap">{note.text}</p>
                      <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(note.createdAt).toLocaleString()}
                          {note.updatedAt !== note.createdAt && ' (edited)'}
                        </span>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => handleEditNote(note.id)}
                            className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-purple-600 dark:hover:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/30 rounded-lg transition-colors"
                            title="Edit note"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteNote(note.id)}
                            className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                            title="Delete note"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No notes yet. Add your first note above!</p>
            </div>
          )}
        </div>
      </div>

      {/* Calendar Summary */}
      {loading ? (
        <div className="card">
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        </div>
      ) : summary ? (
        <div>
          <div className="section-header mb-6">
            <h2 className="section-title dark:text-white">Calendar Summary</h2>
            <p className="section-subtitle dark:text-white">Overview of your calendar activity</p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="stat-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">Total Events</p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white">{summary.total_events}</p>
                </div>
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
                  <Calendar className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
              </div>
            </div>

            <div className="stat-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">Conflicts</p>
                  <p className="text-3xl font-bold text-purple-600 dark:text-purple-400">{summary.events_with_conflicts}</p>
                </div>
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
              </div>
            </div>

            <div className="stat-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">Meeting Hours</p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white">
                    {summary.total_meeting_hours.toFixed(1)}h
                  </p>
                </div>
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
                  <Clock className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
              </div>
            </div>

            <div className="stat-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">Conflict Rate</p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white">
                    {summary.conflict_percentage.toFixed(1)}%
                  </p>
                </div>
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
                  <BarChart3 className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
              </div>
            </div>
          </div>

          {/* Provider Breakdown */}
          <div className="mt-6 grid md:grid-cols-2 gap-4">
            <div className="card-hover">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-4 text-lg">Events by Provider</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Google Calendar</span>
                  </div>
                  <span className="font-bold text-gray-900 dark:text-white text-lg">{summary.google_events}</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                    <span className="text-sm font-medium text-gray-700 dark:text-white">Microsoft Calendar</span>
                  </div>
                  <span className="font-bold text-gray-900 dark:text-white text-lg">{summary.microsoft_events}</span>
                </div>
              </div>
            </div>

            {summary.busiest_day.date && (
              <div className="card-hover">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4 text-lg">Busiest Day</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                    <span className="text-sm font-medium text-gray-700 dark:text-white">Date</span>
                    <span className="font-bold text-gray-900 dark:text-white">
                      {new Date(summary.busiest_day.date).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                    <span className="text-sm font-medium text-gray-700 dark:text-white">Events</span>
                    <span className="font-bold text-gray-900 dark:text-white text-lg">{summary.busiest_day.event_count}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : null}

      {/* No Connections Message */}
      {!user.has_connected_calendars && (
        <div className="card-elevated text-center py-16">
          <div className="w-20 h-20 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <Calendar className="w-10 h-10 text-purple-600" />
          </div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
            No Calendars Connected
          </h3>
          <p className="text-gray-600 dark:text-white mb-8 max-w-md mx-auto text-lg">
            Connect your Google Calendar or Microsoft Calendar to start using the unified calendar system.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button 
              onClick={handleAddGoogleAccount}
              className="btn-google flex items-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>Connect Google</span>
            </button>
            <button 
              onClick={handleAddMicrosoftAccount}
              className="btn-microsoft flex items-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>Connect Microsoft</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
