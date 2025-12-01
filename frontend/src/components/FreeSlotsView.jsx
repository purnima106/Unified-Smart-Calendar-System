import { useState, useEffect } from 'react';
import { Clock, Calendar, Search, Plus, CheckCircle } from 'lucide-react';
import { calendarAPI } from '../services/api';
import LoadingSpinner from './LoadingSpinner';

const FreeSlotsView = ({ user }) => {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [duration, setDuration] = useState(60);
  const [startHour, setStartHour] = useState(0);  // Entire day: 0-24
  const [endHour, setEndHour] = useState(24);     // Entire day: 0-24
  const [freeSlots, setFreeSlots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (selectedDate) {
      findFreeSlots();
    }
  }, [selectedDate, duration, startHour, endHour]);

  const findFreeSlots = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await calendarAPI.getFreeSlots({
        date: selectedDate,
        duration: duration,
        start_hour: startHour,
        end_hour: endHour
      });
      
      if (response.data && response.data.free_slots) {
        setFreeSlots(response.data.free_slots);
        if (response.data.free_slots.length === 0) {
          setError('No free slots found for the selected criteria. Try adjusting the duration or time range.');
        } else {
          setError(''); // Clear error if slots found
        }
      } else {
        setError('Invalid response from server');
        setFreeSlots([]);
      }
    } catch (error) {
      console.error('Error finding free slots:', error);
      const errorMessage = error.response?.data?.error || error.message || 'Failed to find free time slots';
      setError(errorMessage);
      setFreeSlots([]);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (timeString) => {
    return new Date(timeString).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString([], {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const getDurationOptions = () => {
    return [15, 30, 45, 60, 90, 120, 180, 240].map(minutes => ({
      value: minutes,
      label: `${minutes} minutes`
    }));
  };

  const getHourOptions = () => {
    const hours = [];
    // Add 0 (midnight) option
    hours.push({ value: 0, label: '12:00 AM (Midnight)' });
    // Add hours 1-23
    for (let i = 1; i <= 23; i++) {
      hours.push({
        value: i,
        label: `${i}:00 ${i < 12 ? 'AM' : i === 12 ? 'PM (Noon)' : 'PM'}`
      });
    }
    // Add 24 (end of day) option
    hours.push({ value: 24, label: '12:00 AM (End of Day)' });
    return hours;
  };

  const handleSlotSelect = (slot) => {
    // In a real app, this would open a meeting creation form
    console.log('Selected slot:', slot);
    alert(`Selected time slot: ${formatTime(slot.start_time)} - ${formatTime(slot.end_time)}\n\nThis would open a meeting creation form to schedule a meeting in this time slot.`);
  };

  const handleScheduleMeeting = (slot) => {
    console.log('Schedule meeting for slot:', slot);
    alert(`Schedule meeting for: ${formatTime(slot.start_time)} - ${formatTime(slot.end_time)}\n\nThis would open a meeting creation form with the time slot pre-filled.`);
  };

  const handleScheduleNextAvailable = async () => {
    try {
      setLoading(true);
      setError('');
      
      // Find the next available slot
      if (freeSlots.length > 0) {
        const nextSlot = freeSlots[0];
        alert(`Next available slot: ${formatTime(nextSlot.start_time)} - ${formatTime(nextSlot.end_time)}\n\nThis would open a meeting creation form.`);
      } else {
        alert('No free slots available. Try adjusting the search criteria.');
      }
    } catch (error) {
      console.error('Error scheduling next available:', error);
      setError('Failed to find next available slot');
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestMeeting = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await calendarAPI.suggestMeeting({
        duration_minutes: duration,
        preferred_days: [0, 1, 2, 3, 4], // Mon-Fri
        preferred_hours: {
          start: startHour,
          end: endHour
        }
      });
      
      if (response.data.suggestions.length > 0) {
        const suggestions = response.data.suggestions;
        const suggestionText = suggestions.map(s => 
          `${formatDate(s.date)} at ${formatTime(s.slot.start_time)}`
        ).join('\n');
        
        alert(`Suggested meeting times:\n\n${suggestionText}`);
      } else {
        alert('No suitable meeting times found in the next week.');
      }
    } catch (error) {
      console.error('Error suggesting meeting:', error);
      setError('Failed to suggest meeting times');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Free Time Slots</h1>
          <p className="text-gray-600 dark:text-white mt-1">
            Find available time slots for scheduling meetings
          </p>
        </div>
        
        <button
          onClick={handleSuggestMeeting}
          disabled={loading}
          className="btn-primary flex items-center space-x-2"
        >
          {loading ? (
            <LoadingSpinner size="sm" />
          ) : (
            <Search className="w-4 h-4" />
          )}
          <span>Suggest Meeting</span>
        </button>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-700 dark:text-red-300 text-sm">{error}</p>
        </div>
      )}

      {/* Search Controls */}
      <div className="card">
        <h3 className="font-semibold text-gray-900 dark:text-white mb-4">Search Parameters</h3>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-white mb-2">
              Date
            </label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="input"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Duration
            </label>
            <select
              value={duration}
              onChange={(e) => setDuration(parseInt(e.target.value))}
              className="input"
            >
              {getDurationOptions().map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Start Hour
            </label>
            <select
              value={startHour}
              onChange={(e) => setStartHour(parseInt(e.target.value))}
              className="input"
            >
              {getHourOptions().map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              End Hour
            </label>
            <select
              value={endHour}
              onChange={(e) => setEndHour(parseInt(e.target.value))}
              className="input"
            >
              {getHourOptions().map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900 dark:text-white">
            Available Time Slots for {formatDate(selectedDate)}
          </h3>
          <div className="text-sm text-gray-600 dark:text-white">
            {freeSlots.length} slot{freeSlots.length !== 1 ? 's' : ''} found
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner size="lg" />
          </div>
        ) : freeSlots.length > 0 ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {freeSlots.map((slot, index) => (
              <div
                key={index}
                className="border border-gray-200 dark:border-gray-800 rounded-lg p-4 hover:border-purple-300 dark:hover:border-purple-600 hover:shadow-md transition-all cursor-pointer bg-white dark:bg-black"
                onClick={() => handleSlotSelect(slot)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <Clock className="w-4 h-4 text-purple-500 dark:text-purple-400" />
                    <span className="font-medium text-gray-900 dark:text-white">
                      {formatTime(slot.start_time)}
                    </span>
                  </div>
                  <Plus className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                </div>
                
                <div className="text-sm text-gray-600 dark:text-gray-300">
                  <div>Ends: {formatTime(slot.end_time)}</div>
                  <div>Duration: {slot.duration_minutes} minutes</div>
                </div>
                
                <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-800">
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleScheduleMeeting(slot);
                    }}
                    className="w-full btn-primary text-sm"
                  >
                    Schedule Meeting
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <Clock className="w-16 h-16 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              No Free Slots Found
            </h3>
            <p className="text-gray-600 dark:text-white mb-4">
              No available time slots found for the selected criteria. Try adjusting the duration or time range.
            </p>
            <div className="flex items-center justify-center space-x-4">
              <button
                onClick={() => setDuration(30)}
                className="btn-secondary text-sm"
              >
                Try 30 minutes
              </button>
              <button
                onClick={() => {
                  setStartHour(8);
                  setEndHour(18);
                }}
                className="btn-secondary text-sm"
              >
                Extend Hours
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="card">
          <div className="flex items-center space-x-3 mb-3">
            <Calendar className="w-5 h-5 text-purple-500 dark:text-purple-400" />
            <h3 className="font-semibold text-gray-900 dark:text-white">Quick Schedule</h3>
          </div>
          <p className="text-sm text-gray-600 dark:text-white mb-4">
            Schedule a meeting for the next available slot
          </p>
          <button 
            onClick={handleScheduleNextAvailable}
            disabled={loading}
            className="btn-primary w-full"
          >
            {loading ? 'Finding...' : 'Schedule Next Available'}
          </button>
        </div>

        <div className="card">
          <div className="flex items-center space-x-3 mb-3">
            <CheckCircle className="w-5 h-5 text-purple-500 dark:text-purple-400" />
            <h3 className="font-semibold text-gray-900 dark:text-white">Meeting Suggestions</h3>
          </div>
          <p className="text-sm text-gray-600 dark:text-white mb-4">
            Get AI-powered suggestions for optimal meeting times
          </p>
          <button
            onClick={handleSuggestMeeting}
            disabled={loading}
            className="btn-secondary w-full"
          >
            Get Suggestions
          </button>
        </div>
      </div>

      {/* Tips */}
      <div className="card bg-purple-50 dark:bg-purple-900/30 border-purple-200 dark:border-purple-800">
        <h3 className="font-semibold text-purple-900 dark:text-purple-200 mb-3">Tips for Finding Free Slots</h3>
        <div className="space-y-2 text-sm text-purple-800 dark:text-purple-200">
          <p>• Try shorter meeting durations (15-30 minutes) for more options</p>
          <p>• Extend your working hours to find more available times</p>
          <p>• Check different dates if today is fully booked</p>
          <p>• Use the meeting suggestions feature for optimal scheduling</p>
          <p>• Consider scheduling meetings during lunch breaks or early/late hours</p>
        </div>
      </div>
    </div>
  );
};

export default FreeSlotsView;
