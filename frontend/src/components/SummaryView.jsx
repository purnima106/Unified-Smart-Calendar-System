import { useState, useEffect } from 'react';
import { BarChart3, Calendar, Clock, AlertTriangle, TrendingUp, Users, MapPin, List, RefreshCw, Mail, Video } from 'lucide-react';
import { calendarAPI } from '../services/api';
import LoadingSpinner from './LoadingSpinner';

const SummaryView = ({ user }) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dateRange, setDateRange] = useState('30'); // days
  const [showEventHistory, setShowEventHistory] = useState(true);

  useEffect(() => {
    loadSummary();
  }, [dateRange]);

  const loadSummary = async () => {
    try {
      setLoading(true);
      setError('');
      
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - parseInt(dateRange));
      
      const response = await calendarAPI.getSummary({
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString()
      });
      
      setSummary(response.data);
    } catch (error) {
      console.error('Error loading summary:', error);
      setError('Failed to load calendar summary');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getConflictSeverity = (percentage) => {
    if (percentage < 5) return { level: 'Low', color: 'text-purple-600', bg: 'bg-purple-100' };
    if (percentage < 15) return { level: 'Medium', color: 'text-purple-600', bg: 'bg-purple-100' };
    return { level: 'High', color: 'text-purple-600', bg: 'bg-purple-100' };
  };

  const getProductivityScore = (summary) => {
    if (!summary) return 0;
    
    const totalHours = summary.total_meeting_hours;
    const conflictRate = summary.conflict_percentage;
    const eventCount = summary.total_events;
    
    // Simple scoring algorithm
    let score = 100;
    
    // Deduct points for conflicts
    score -= conflictRate * 2;
    
    // Bonus for reasonable meeting hours (not too few, not too many)
    if (totalHours < 5) score -= 10;
    else if (totalHours > 40) score -= 15;
    
    // Bonus for having events (shows engagement)
    if (eventCount > 0) score += 5;
    
    return Math.max(0, Math.min(100, Math.round(score)));
  };

  const getProductivityLevel = (score) => {
    if (score >= 80) return { level: 'Excellent', color: 'text-purple-600', bg: 'bg-purple-100' };
    if (score >= 60) return { level: 'Good', color: 'text-purple-600', bg: 'bg-purple-100' };
    if (score >= 40) return { level: 'Fair', color: 'text-purple-600', bg: 'bg-purple-100' };
    return { level: 'Needs Improvement', color: 'text-purple-600', bg: 'bg-purple-100' };
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
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">Calendar Summary</h1>
          <p className="text-gray-600 dark:text-gray-300 text-lg">
            Analytics and insights about your calendar usage
          </p>
        </div>
        
        <div className="flex items-center space-x-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="input w-auto min-w-[140px]"
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
          </select>
          
          <button
            onClick={loadSummary}
            className="btn-secondary flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Refresh</span>
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

      {summary ? (
        <>
          {/* Key Metrics */}
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
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">Meeting Hours</p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white">
                    {summary.total_meeting_hours.toFixed(1)}h
                  </p>
                </div>
                <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
                  <Clock className="w-6 h-6 text-purple-600" />
                </div>
              </div>
            </div>

            <div className="stat-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-300 mb-1">Conflicts</p>
                  <p className="text-3xl font-bold text-purple-600 dark:text-purple-400">{summary.events_with_conflicts}</p>
                </div>
                <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6 text-purple-600" />
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
                <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
                  <BarChart3 className="w-6 h-6 text-purple-600" />
                </div>
              </div>
            </div>
          </div>

          {/* Productivity Score */}
          <div className="card-hover">
            <h3 className="font-bold text-gray-900 dark:text-white mb-6 text-lg">Calendar Productivity Score</h3>
            <div className="flex items-center space-x-6">
              <div className="flex-1">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Overall Score</span>
                  <span className="text-lg font-bold text-gray-900 dark:text-white">
                    {getProductivityScore(summary)}/100
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-purple-500 to-purple-600 h-3 rounded-full transition-all duration-500 shadow-sm"
                    style={{ width: `${getProductivityScore(summary)}%` }}
                  ></div>
                </div>
              </div>
              <div className={`px-4 py-2 rounded-xl text-sm font-bold ${getProductivityLevel(getProductivityScore(summary)).bg} ${getProductivityLevel(getProductivityScore(summary)).color}`}>
                {getProductivityLevel(getProductivityScore(summary)).level}
              </div>
            </div>
          </div>

          {/* Provider Breakdown */}
          <div className="grid md:grid-cols-2 gap-6">
            <div className="card-hover">
              <h3 className="font-bold text-gray-900 dark:text-white mb-5 text-lg">Events by Provider</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                  <div className="flex items-center space-x-3">
                    <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Google Calendar</span>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-gray-900 dark:text-white text-lg">{summary.google_events}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {summary.total_events > 0 ? ((summary.google_events / summary.total_events) * 100).toFixed(1) : 0}%
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                  <div className="flex items-center space-x-3">
                    <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Microsoft Calendar</span>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-gray-900 dark:text-white text-lg">{summary.microsoft_events}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {summary.total_events > 0 ? ((summary.microsoft_events / summary.total_events) * 100).toFixed(1) : 0}%
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="card-hover">
              <h3 className="font-bold text-gray-900 dark:text-white mb-5 text-lg">Conflict Analysis</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Conflict Severity</span>
                  <div className={`px-3 py-1.5 rounded-lg text-xs font-bold ${getConflictSeverity(summary.conflict_percentage).bg} dark:bg-purple-900/30 ${getConflictSeverity(summary.conflict_percentage).color} dark:text-purple-300`}>
                    {getConflictSeverity(summary.conflict_percentage).level}
                  </div>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Conflicts per Day</span>
                  <span className="font-bold text-gray-900 dark:text-white">
                    {(summary.events_with_conflicts / parseInt(dateRange)).toFixed(1)}
                  </span>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Date Range</span>
                  <span className="font-bold text-gray-900 dark:text-white text-sm">
                    {formatDate(summary.date_range.start)} - {formatDate(summary.date_range.end)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Busiest Day */}
          {summary.busiest_day.date && (
            <div className="card-hover">
              <h3 className="font-bold text-gray-900 dark:text-white mb-5 text-lg">Busiest Day</h3>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xl font-bold text-gray-900 dark:text-white mb-1">
                    {formatDate(summary.busiest_day.date)}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-300">
                    {summary.busiest_day.event_count} events scheduled
                  </p>
                </div>
                <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center shadow-md">
                  <Calendar className="w-8 h-8 text-purple-600 dark:text-purple-400" />
                </div>
              </div>
            </div>
          )}

          {/* Event History */}
          {summary.events && summary.events.length > 0 && (
            <div className="card-hover">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
                    <List className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-900 dark:text-white text-lg">Event History</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      Complete list of {summary.total_events} unique event{summary.total_events !== 1 ? 's' : ''} in the selected period
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setShowEventHistory(!showEventHistory)}
                  className="px-4 py-2 text-sm font-medium text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/30 rounded-lg transition-colors"
                >
                  {showEventHistory ? 'Hide' : 'Show'} History
                </button>
              </div>
              
              {showEventHistory ? (
                <div className="space-y-3 max-h-[600px] overflow-y-auto">
                  {summary.events.map((event, index) => {
                    const eventDate = new Date(event.start_time);
                    const eventEndDate = new Date(event.end_time);
                    const isToday = eventDate.toDateString() === new Date().toDateString();
                    const isPast = eventEndDate < new Date();
                    
                    return (
                      <div
                        key={event.id || index}
                        className={`p-4 rounded-xl border-2 transition-all duration-200 ${
                          event.has_conflict
                            ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 hover:border-red-300 dark:hover:border-red-700'
                            : isPast
                            ? 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                            : 'bg-white dark:bg-black border-purple-100 dark:border-purple-900/50 hover:border-purple-200 dark:hover:border-purple-800'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-2 mb-2">
                              <h4 className="font-semibold text-gray-900 dark:text-white text-base">
                                {event.display_title || event.title}
                              </h4>
                              {event.is_synced && (
                                <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 text-xs font-medium rounded-full flex items-center space-x-1">
                                  <RefreshCw className="w-3 h-3" />
                                  <span>Synced</span>
                                </span>
                              )}
                              {event.has_conflict && (
                                <span className="px-2 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-xs font-medium rounded-full flex items-center space-x-1">
                                  <AlertTriangle className="w-3 h-3" />
                                  <span>Conflict</span>
                                </span>
                              )}
                              {isPast && (
                                <span className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs font-medium rounded-full">
                                  Past
                                </span>
                              )}
                              {isToday && !isPast && (
                                <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 text-xs font-medium rounded-full">
                                  Today
                                </span>
                              )}
                            </div>
                            
                            <div className="space-y-1.5 text-sm text-gray-600 dark:text-gray-300">
                              <div className="flex items-center space-x-2">
                                <Calendar className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                                <span>
                                  {eventDate.toLocaleDateString('en-US', {
                                    weekday: 'short',
                                    year: 'numeric',
                                    month: 'short',
                                    day: 'numeric'
                                  })}
                                </span>
                              </div>
                              
                              <div className="flex items-center space-x-2">
                                <Clock className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                                <span>
                                  {eventDate.toLocaleTimeString('en-US', {
                                    hour: '2-digit',
                                    minute: '2-digit'
                                  })} - {eventEndDate.toLocaleTimeString('en-US', {
                                    hour: '2-digit',
                                    minute: '2-digit'
                                  })}
                                </span>
                              </div>
                              
                              <div className="flex items-center space-x-2">
                                <Mail className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                                <span className="text-purple-600 dark:text-purple-400 font-medium">
                                  {event.organizer || 'Unknown Account'}
                                </span>
                                <span className="text-gray-400 dark:text-gray-500">•</span>
                                <span className="capitalize">{event.provider}</span>
                              </div>
                              
                            {event.location && (
                              <div className="flex items-center space-x-2">
                                <MapPin className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                                <span className="truncate">{event.location}</span>
                              </div>
                            )}
                            
                            {event.meet_link && (
                              <div className="flex items-center space-x-2">
                                <Video className="w-4 h-4 text-purple-500 dark:text-purple-400" />
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    window.open(event.meet_link, '_blank');
                                  }}
                                  className="text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 font-medium text-sm underline"
                                >
                                  Join Google Meet
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                        
                        <div className="ml-4 flex flex-col items-end">
                          <div className="w-3 h-3 rounded-full mb-2 bg-purple-500"></div>
                          {event.all_day && (
                            <span className="text-xs text-gray-500 dark:text-gray-400">All Day</span>
                          )}
                          {event.meet_link && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                window.open(event.meet_link, '_blank');
                              }}
                              className="mt-2 p-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                              title="Join Google Meet"
                            >
                              <Video className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <button
                    onClick={() => setShowEventHistory(true)}
                    className="text-purple-600 hover:text-purple-700 font-medium"
                  >
                    Click to view {summary.events.length} event{summary.events.length !== 1 ? 's' : ''}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Insights and Recommendations */}
          <div className="card bg-gradient-to-r from-purple-50 to-purple-100 border-purple-200">
            <div className="flex items-start space-x-3 mb-4">
              <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center flex-shrink-0">
                <TrendingUp className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="font-bold text-purple-900 mb-4 text-lg">Insights & Recommendations</h3>
                <div className="space-y-3 text-sm text-purple-800">
                  {summary.conflict_percentage > 10 && (
                    <p className="flex items-start"><span className="font-semibold mr-2">⚠️</span> Your conflict rate is higher than average. Consider reviewing your scheduling habits.</p>
                  )}
                  
                  {summary.total_meeting_hours > 30 && (
                    <p className="flex items-start"><span className="font-semibold mr-2">📅</span> You have many meetings scheduled. Consider blocking focus time for deep work.</p>
                  )}
                  
                  {summary.total_meeting_hours < 5 && (
                    <p className="flex items-start"><span className="font-semibold mr-2">📊</span> Your calendar shows few meetings. This might indicate low engagement or missed opportunities.</p>
                  )}
                  
                  {summary.google_events > 0 && summary.microsoft_events > 0 && (
                    <p className="flex items-start"><span className="font-semibold mr-2">🔄</span> You're using multiple calendar providers. Great for flexibility, but watch for conflicts!</p>
                  )}
                  
                  {getProductivityScore(summary) < 50 && (
                    <p className="flex items-start"><span className="font-semibold mr-2">🎯</span> Your productivity score suggests room for improvement. Try using the Free Slots feature for better scheduling.</p>
                  )}
                  
                  {summary.events_with_conflicts === 0 && (
                    <p className="flex items-start"><span className="font-semibold mr-2">✅</span> Excellent! No conflicts detected. Your calendar management is on point.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="card-elevated text-center py-16">
          <div className="w-20 h-20 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <BarChart3 className="w-10 h-10 text-purple-600" />
          </div>
          <h3 className="text-2xl font-bold text-gray-900 mb-3">
            No Data Available
          </h3>
          <p className="text-gray-600 mb-8 max-w-md mx-auto text-lg">
            No calendar data found for the selected time period. Try syncing your calendars or selecting a different date range.
          </p>
          <button
            onClick={loadSummary}
            className="btn-primary"
          >
            Refresh Data
          </button>
        </div>
      )}
    </div>
  );
};

export default SummaryView;
