import { useState, useEffect } from 'react';
import { AlertTriangle, Clock, Calendar, Users, MapPin, User, Video } from 'lucide-react';
import { calendarAPI } from '../services/api';
import LoadingSpinner from './LoadingSpinner';

const ConflictsView = ({ user }) => {
  const [conflicts, setConflicts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [resolving, setResolving] = useState(false);

  useEffect(() => {
    loadConflicts();
  }, []);

  const loadConflicts = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await calendarAPI.getConflicts();
      setConflicts(response.data.conflicts);
    } catch (error) {
      console.error('Error loading conflicts:', error);
      setError('Failed to load calendar conflicts');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (timeString) => {
    return new Date(timeString).toLocaleString();
  };

  const formatDuration = (startTime, endTime) => {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const durationMs = end - start;
    const hours = Math.floor(durationMs / (1000 * 60 * 60));
    const minutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  const getAccountEmail = (event) => {
    // Try organizer field first
    if (event.organizer && typeof event.organizer === 'string' && event.organizer.includes('@')) {
      return event.organizer.trim();
    }
    // Fallback to extracting from provider_event_id (format: email:event_id)
    if (event.provider_event_id && event.provider_event_id.includes('@') && event.provider_event_id.includes(':')) {
      const parts = event.provider_event_id.split(':');
      if (parts.length >= 2 && parts[0].includes('@')) {
        return parts[0].trim();
      }
    }
    return null;
  };

  const handleViewDetails = (conflict) => {
    console.log('View details for conflict:', conflict);
    const accountEmail = getAccountEmail(conflict.event);
    const emailInfo = accountEmail ? `\nAccount: ${accountEmail}` : '';
    alert(`Event: ${conflict.event.title}${emailInfo}\nTime: ${formatTime(conflict.event.start_time)} - ${formatTime(conflict.event.end_time)}\nProvider: ${conflict.event.provider}`);
  };

  const handleResolveConflict = async (conflict) => {
    try {
      setResolving(true);
      console.log('Resolving conflict:', conflict);
      
      // In a real app, this would open a resolution dialog
      // For now, we'll just mark it as resolved
      alert(`Conflict resolution for: ${conflict.event.title}\n\nThis would open a dialog to:\n- Reschedule one of the meetings\n- Cancel one of the meetings\n- Merge the meetings\n- Mark as resolved`);
      
      // Remove the conflict from the list (simulate resolution)
      setConflicts(prev => prev.filter(c => c.event.id !== conflict.event.id));
      
    } catch (error) {
      console.error('Error resolving conflict:', error);
      setError('Failed to resolve conflict');
    } finally {
      setResolving(false);
    }
  };

  const handleDismissConflict = (conflict) => {
    console.log('Dismissing conflict:', conflict);
    
    // Remove the conflict from the list
    setConflicts(prev => prev.filter(c => c.event.id !== conflict.event.id));
  };

  const handleViewCalendar = () => {
    // Navigate to calendar view
    window.location.href = '/calendar';
  };

  const getProviderBadge = (provider) => {
    const isGoogle = provider === 'google';
    return (
      <span className={`badge ${isGoogle ? 'badge-google' : 'badge-microsoft'}`}>
        {isGoogle ? 'Google' : 'Microsoft'}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">Calendar Conflicts</h1>
          <p className="text-gray-600 dark:text-gray-300 text-lg">
            Identify and resolve overlapping meetings across your calendars
          </p>
        </div>
        
        <button
          onClick={loadConflicts}
          className="btn-secondary flex items-center space-x-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>Refresh</span>
        </button>
      </div>

      {error && (
        <div className="bg-purple-50 dark:bg-purple-900/30 border-l-4 border-purple-500 dark:border-purple-400 rounded-lg p-4 shadow-sm">
          <div className="flex items-start">
            <AlertTriangle className="w-5 h-5 text-purple-600 dark:text-purple-400 mt-0.5 flex-shrink-0" />
            <p className="text-purple-800 dark:text-purple-200 text-sm ml-3">{error}</p>
          </div>
        </div>
      )}

      {/* Conflicts Summary */}
      {conflicts.length > 0 && (
        <div className="card-elevated">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              {conflicts.length} Conflict{conflicts.length !== 1 ? 's' : ''} Found
            </h2>
          </div>
          
          <div className="grid md:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
              <p className="text-3xl font-bold text-purple-600 dark:text-purple-400 mb-1">{conflicts.length}</p>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-300">Total Conflicts</p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
              <p className="text-3xl font-bold text-gray-900 dark:text-white mb-1">
                {conflicts.filter(c => c.event.provider === 'google').length}
              </p>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-300">Google Events</p>
            </div>
            <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-xl">
              <p className="text-3xl font-bold text-gray-900 dark:text-white mb-1">
                {conflicts.filter(c => c.event.provider === 'microsoft').length}
              </p>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-300">Microsoft Events</p>
            </div>
          </div>
        </div>
      )}

      {/* Conflicts List */}
      {conflicts.length > 0 ? (
        <div className="space-y-4">
          {conflicts.map((conflict, index) => (
            <div key={index} className="card-hover border-l-4 border-purple-500">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center flex-wrap gap-3 mb-4">
                    <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                      <AlertTriangle className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                    </div>
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                      {conflict.event.title}
                    </h3>
                    {getProviderBadge(conflict.event.provider)}
                    <span className="badge-conflict">Conflict</span>
                    {getAccountEmail(conflict.event) && (
                      <span className="badge bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300 px-3 py-1 rounded-full text-xs font-medium">
                        📧 {getAccountEmail(conflict.event)}
                      </span>
                    )}
                  </div>
                  
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-300">
                        <Clock className="w-4 h-4" />
                        <span>
                          {formatTime(conflict.event.start_time)} - {formatTime(conflict.event.end_time)}
                        </span>
                      </div>
                      
                      <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-300">
                        <Calendar className="w-4 h-4" />
                        <span>
                          Duration: {formatDuration(conflict.event.start_time, conflict.event.end_time)}
                        </span>
                      </div>
                      
                      {conflict.event.location && (
                        <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-300">
                          <MapPin className="w-4 h-4" />
                          <span>{conflict.event.location}</span>
                        </div>
                      )}
                      
                      {getAccountEmail(conflict.event) && (
                        <div className="flex items-center space-x-2 text-sm font-medium text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-900/30 px-3 py-2 rounded-lg">
                          <User className="w-4 h-4" />
                          <span>Gmail Account: {getAccountEmail(conflict.event)}</span>
                        </div>
                      )}
                      
                      {conflict.event.meet_link && (
                        <button
                          onClick={() => window.open(conflict.event.meet_link, '_blank')}
                          className="flex items-center space-x-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg transition-colors w-full"
                        >
                          <Video className="w-4 h-4" />
                          <span>Join Google Meet</span>
                        </button>
                      )}
                    </div>
                    
                    <div className="space-y-2">
                      <h4 className="font-medium text-gray-900 dark:text-white">Conflicting Events:</h4>
                      <div className="space-y-3">
                        {conflict.conflicting_events_details && conflict.conflicting_events_details.length > 0 ? (
                          conflict.conflicting_events_details.map((conflictingEvent, eventIndex) => {
                            const conflictingAccountEmail = getAccountEmail(conflictingEvent);
                            return (
                              <div key={eventIndex} className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-400 dark:border-red-600 p-3 rounded">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="font-semibold text-gray-900 dark:text-white">{conflictingEvent.title}</span>
                                  <div className="flex items-center space-x-2">
                                    {getProviderBadge(conflictingEvent.provider)}
                                    {conflictingEvent.meet_link && (
                                      <button
                                        onClick={() => window.open(conflictingEvent.meet_link, '_blank')}
                                        className="p-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded transition-colors"
                                        title="Join Google Meet"
                                      >
                                        <Video className="w-3 h-3" />
                                      </button>
                                    )}
                                  </div>
                                </div>
                                <div className="text-xs text-gray-600 dark:text-gray-300 space-y-1">
                                  <div>Time: {formatTime(conflictingEvent.start_time)} - {formatTime(conflictingEvent.end_time)}</div>
                                  {conflictingAccountEmail && (
                                    <div className="font-medium text-purple-700 dark:text-purple-300 mt-1">
                                      📧 Account: {conflictingAccountEmail}
                                    </div>
                                  )}
                                </div>
                              </div>
                            );
                          })
                        ) : (
                          conflict.conflicting_events.map((eventId, eventIndex) => (
                            <div key={eventIndex} className="text-sm text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 p-2 rounded">
                              Event ID: {eventId}
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {conflict.event.description && (
                    <div className="mt-3">
                      <p className="text-sm text-gray-600 dark:text-gray-300">{conflict.event.description}</p>
                    </div>
                  )}
                  
                  {conflict.event.attendees && conflict.event.attendees.length > 0 && (
                    <div className="mt-3">
                      <div className="flex items-center space-x-2 mb-2">
                        <Users className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Attendees:</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {conflict.event.attendees.map((attendee, attendeeIndex) => (
                          <span key={attendeeIndex} className="text-xs bg-gray-100 dark:bg-gray-800 dark:text-gray-300 px-2 py-1 rounded">
                            {attendee.name || attendee.email}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              
              {/* Action Buttons */}
              <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-800">
                <div className="flex flex-wrap items-center gap-3">
                  <button 
                    onClick={() => handleViewDetails(conflict)}
                    className="btn-secondary text-sm"
                  >
                    View Details
                  </button>
                  <button 
                    onClick={() => handleResolveConflict(conflict)}
                    disabled={resolving}
                    className="btn-primary text-sm"
                  >
                    {resolving ? 'Resolving...' : 'Resolve Conflict'}
                  </button>
                  <button 
                    onClick={() => handleDismissConflict(conflict)}
                    className="text-sm text-gray-500 dark:text-gray-400 hover:text-purple-600 dark:hover:text-purple-400 font-medium transition-colors"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* No Conflicts Message */
        <div className="card-elevated text-center py-16">
          <div className="w-20 h-20 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
            <AlertTriangle className="w-10 h-10 text-purple-600 dark:text-purple-400" />
          </div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
            No Conflicts Found
          </h3>
          <p className="text-gray-600 dark:text-gray-300 mb-8 max-w-md mx-auto text-lg">
            Great! Your calendar is conflict-free. All your meetings are properly scheduled without overlaps.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={loadConflicts}
              className="btn-secondary"
            >
              Check Again
            </button>
            <button 
              onClick={handleViewCalendar}
              className="btn-primary"
            >
              View Calendar
            </button>
          </div>
        </div>
      )}

      {/* Conflict Resolution Tips */}
      {conflicts.length > 0 && (
        <div className="card bg-gradient-to-r from-purple-50 to-purple-100 border-purple-200">
          <div className="flex items-start space-x-3 mb-4">
            <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1">
              <h3 className="font-bold text-purple-900 mb-3 text-lg">Conflict Resolution Tips</h3>
              <div className="space-y-2.5 text-sm text-purple-800">
                <p className="flex items-start"><span className="font-semibold mr-2">•</span> Review conflicting events and determine which one is more important</p>
                <p className="flex items-start"><span className="font-semibold mr-2">•</span> Consider rescheduling one of the meetings to a different time</p>
                <p className="flex items-start"><span className="font-semibold mr-2">•</span> Check if any meetings can be combined or shortened</p>
                <p className="flex items-start"><span className="font-semibold mr-2">•</span> Use the Free Slots feature to find alternative meeting times</p>
                <p className="flex items-start"><span className="font-semibold mr-2">•</span> Communicate with meeting organizers about the conflict</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConflictsView;
