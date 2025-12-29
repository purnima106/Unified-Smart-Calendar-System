import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { publicBookingAPI } from '../services/api';
import LoadingSpinner from './LoadingSpinner';

const durations = [30, 60];

const PublicBookingPage = () => {
  const { username } = useParams();
  const [duration, setDuration] = useState(30);
  const [slots, setSlots] = useState([]);
  // Important: Do NOT unmount/remount FullCalendar during slot fetching,
  // otherwise datesSet will retrigger and cause an infinite refresh loop.
  const [initialLoading, setInitialLoading] = useState(true);
  const [fetchingSlots, setFetchingSlots] = useState(false);
  const [error, setError] = useState('');
  const latestRequestIdRef = useRef(0);

  const [selectedSlot, setSelectedSlot] = useState(null);
  const [clientName, setClientName] = useState('');
  const [clientEmail, setClientEmail] = useState('');
  const [clientNote, setClientNote] = useState('');
  const [manualMeetingLink, setManualMeetingLink] = useState('');
  const [useManualLink, setUseManualLink] = useState(false);
  const [booking, setBooking] = useState(null);
  const [bookingSubmitting, setBookingSubmitting] = useState(false);
  const [availableProviders, setAvailableProviders] = useState(['google', 'microsoft']);
  const [meetingProvider, setMeetingProvider] = useState('google');

  const defaultRange = useMemo(() => {
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    const end = new Date(start);
    end.setDate(end.getDate() + 14);
    end.setHours(23, 59, 59, 999);
    return { start, end };
  }, []);

  const loadSlots = async (range, { silent = false } = {}) => {
    const requestId = ++latestRequestIdRef.current;
    try {
      if (!silent) setInitialLoading(true);
      setFetchingSlots(true);
      setError('');
      const params = {
        start: range.start.toISOString(),
        end: range.end.toISOString(),
        duration_minutes: duration,
      };
      const res = await publicBookingAPI.getSlots(username, params);
      // Ignore out-of-order responses
      if (requestId !== latestRequestIdRef.current) return;
      setSlots(res.data.slots || []);
      const providers = res.data.available_providers || [];
      setAvailableProviders(providers);
      setMeetingProvider((prev) => {
        if (providers.includes(prev)) return prev;
        return providers[0] || 'google';
      });
    } catch (e) {
      if (requestId !== latestRequestIdRef.current) return;
      setError(e.response?.data?.error || e.message || 'Failed to load slots');
      setSlots([]);
    } finally {
      if (requestId !== latestRequestIdRef.current) return;
      setFetchingSlots(false);
      setInitialLoading(false);
    }
  };

  useEffect(() => {
    setBooking(null);
    setSelectedSlot(null);
    loadSlots(defaultRange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [username, duration]);

  const calendarEvents = useMemo(() => {
    return (slots || []).map((s, idx) => ({
      id: `${s.start_time}-${idx}`,
      title: '✓ Available - Click to Book',
      start: s.start_time,
      end: s.end_time,
      backgroundColor: '#7c3aed',
      borderColor: '#6d28d9',
      textColor: '#ffffff',
      classNames: ['cursor-pointer', 'hover:opacity-90'],
      extendedProps: {
        duration_minutes: s.duration_minutes,
      },
    }));
  }, [slots]);

  const handleDatesSet = (arg) => {
    // Fetch slots for the visible range
    const start = arg.start;
    const end = arg.end;
    // Silent refresh: keep calendar mounted to avoid refresh loop.
    loadSlots({ start, end }, { silent: true });
  };

  const handleSlotClick = (clickInfo) => {
    const start = clickInfo.event.start;
    const end = clickInfo.event.end;
    
    // Normalize times to remove milliseconds and ensure consistent format
    const normalizedStart = new Date(start);
    normalizedStart.setMilliseconds(0);
    normalizedStart.setSeconds(0);
    
    const normalizedEnd = new Date(end);
    normalizedEnd.setMilliseconds(0);
    normalizedEnd.setSeconds(0);
    
    // #region agent log
    fetch('http://127.0.0.1:7243/ingest/a5961e26-d5d0-4d51-aab5-b97177e140f5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PublicBookingPage.jsx:98',message:'Slot clicked - times before normalization',data:{original_start:start.toISOString(),original_end:end.toISOString(),duration:duration},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    
    console.log('Selected slot:', {
      original: { start: start.toISOString(), end: end.toISOString() },
      normalized: { start: normalizedStart.toISOString(), end: normalizedEnd.toISOString() },
      duration: duration
    });
    
    // #region agent log
    fetch('http://127.0.0.1:7243/ingest/a5961e26-d5d0-4d51-aab5-b97177e140f5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PublicBookingPage.jsx:115',message:'Slot clicked - normalized times',data:{normalized_start:normalizedStart.toISOString(),normalized_end:normalizedEnd.toISOString(),duration:duration},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    
    setSelectedSlot({
      start_time: normalizedStart.toISOString(),
      end_time: normalizedEnd.toISOString(),
      duration_minutes: duration,
    });
    setBooking(null);
    setError('');
    // Scroll to booking form
    setTimeout(() => {
      const formElement = document.getElementById('booking-form');
      if (formElement) {
        formElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 100);
  };

  const detectProviderFromEmail = (value) => {
    const lower = value.toLowerCase();
    if (availableProviders.includes('google') && lower.includes('@gmail')) {
      return 'google';
    }
    if (
      availableProviders.includes('microsoft') &&
      (lower.includes('@outlook') || lower.includes('@hotmail') || lower.includes('@live') || lower.includes('@microsoft'))
    ) {
      return 'microsoft';
    }
    return null;
  };

  const handleClientEmailChange = (value) => {
    setClientEmail(value);
    const inferred = detectProviderFromEmail(value);
    if (inferred) {
      setMeetingProvider(inferred);
    }
  };

  const submitBooking = async () => {
    if (!selectedSlot) return;
    if (!clientName.trim()) return setError('Please enter your name');
    if (!clientEmail.includes('@')) return setError('Please enter a valid email');
    if (useManualLink && !manualMeetingLink.trim()) {
      return setError('Please enter a meeting link or uncheck "Use manual meeting link"');
    }

    try {
      setBookingSubmitting(true);
      setError('');
      const payload = {
        username,
        client_name: clientName.trim(),
        client_email: clientEmail.trim(),
        client_note: clientNote.trim(),
        start_time: selectedSlot.start_time,
        end_time: selectedSlot.end_time,
        duration_minutes: selectedSlot.duration_minutes,
        meeting_provider: meetingProvider,
      };
      
      // If manual link is provided, include it
      if (useManualLink && manualMeetingLink.trim()) {
        payload.manual_meeting_link = manualMeetingLink.trim();
      }
      
      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/a5961e26-d5d0-4d51-aab5-b97177e140f5',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PublicBookingPage.jsx:163',message:'Submitting booking payload',data:payload,timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      console.log('Submitting booking:', payload);
      const res = await publicBookingAPI.book(payload);
      console.log('Booking response:', res);
      
      if (res.data && res.data.booking) {
        setBooking(res.data.booking);
        setSelectedSlot(null);
        setClientName('');
        setClientEmail('');
        setClientNote('');
        setManualMeetingLink('');
        setUseManualLink(false);
        await loadSlots(defaultRange);
      } else {
        setError('Unexpected response format from server');
      }
    } catch (e) {
      console.error('Booking error:', e);
      const status = e.response?.status;
      const errorData = e.response?.data;
      
      if (status === 409) {
        setError('Slot no longer available. Please pick another time.');
        await loadSlots(defaultRange);
      } else {
        // Show detailed error message
        const errorMsg = errorData?.error || errorData?.message || e.message || 'Booking failed. Please try again.';
        setError(`Booking failed: ${errorMsg}`);
        console.error('Full error response:', errorData);
      }
    } finally {
      setBookingSubmitting(false);
    }
  };

  const providerOptions = [
    { key: 'google', label: 'Google Meet' },
    { key: 'microsoft', label: 'Microsoft Teams' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-purple-50">
      <div className="max-w-5xl mx-auto px-6 py-10 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Book a meeting</h1>
            <p className="text-gray-600 mt-1">
              Select an available time slot for <span className="font-semibold text-purple-700">{username}</span>
            </p>
          </div>
          <Link to="/login" className="text-sm font-semibold text-purple-700 hover:text-purple-800">
            Owner login
          </Link>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl shadow-sm p-5">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="text-sm text-gray-700">
              Slot duration
            </div>
            <div className="flex items-center gap-2">
              {durations.map((d) => (
                <button
                  key={d}
                  onClick={() => setDuration(d)}
                  className={`px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
                    duration === d
                      ? 'bg-purple-600 text-white'
                      : 'bg-purple-50 text-purple-700 hover:bg-purple-100'
                  }`}
                >
                  {d} min
                </button>
              ))}
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-purple-50 border-l-4 border-purple-500 rounded-lg p-4">
            <p className="text-purple-800 text-sm font-medium">{error}</p>
          </div>
        )}

        <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden relative">
          <FullCalendar
            plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
            initialView="timeGridWeek"
            headerToolbar={{
              left: 'prev,next today',
              center: 'title',
              right: 'timeGridWeek,timeGridDay,dayGridMonth',
            }}
            events={calendarEvents}
            datesSet={handleDatesSet}
            eventClick={handleSlotClick}
            eventDisplay="block"
            height="auto"
            nowIndicator={true}
            timeZone="local"
            slotDuration="00:30:00"
            slotMinTime="06:00:00"
            slotMaxTime="22:00:00"
            eventMouseEnter={(info) => {
              info.el.style.cursor = 'pointer';
              info.el.style.opacity = '0.9';
            }}
            eventMouseLeave={(info) => {
              info.el.style.opacity = '1';
            }}
          />

          {(initialLoading || fetchingSlots) && (
            <div className="absolute inset-0 bg-white/70 backdrop-blur-sm flex items-center justify-center">
              <div className="flex items-center gap-3 bg-white border border-gray-200 rounded-xl px-4 py-3 shadow-sm">
                <LoadingSpinner size="sm" />
                <span className="text-sm font-semibold text-gray-700">
                  Loading available slots…
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Booking form */}
        {selectedSlot && (
          <div id="booking-form" className="bg-white border-2 border-purple-500 rounded-2xl shadow-lg p-6 space-y-4 animate-in fade-in slide-in-from-bottom-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Book this time slot</h2>
                <p className="text-sm text-gray-600 mt-1">Fill in your details to schedule the meeting</p>
              </div>
              <button
                onClick={() => {
                  setSelectedSlot(null);
                  setClientName('');
                  setClientEmail('');
                  setClientNote('');
                  setError('');
                }}
                className="text-sm font-semibold text-gray-500 hover:text-gray-700"
              >
                Cancel
              </button>
            </div>

            <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <div className="text-sm text-gray-700">
                  <span className="font-semibold text-purple-900">Selected time:</span>{' '}
                  <span className="font-bold text-gray-900">{new Date(selectedSlot.start_time).toLocaleString('en-US', { 
                    weekday: 'long', 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit'
                  })}</span>
                  {' '}({selectedSlot.duration_minutes} minutes)
                </div>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Name</label>
                <input
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="Your name"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Email</label>
                <input
                  value={clientEmail}
                  onChange={(e) => handleClientEmailChange(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="you@company.com"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Note (optional)</label>
              <textarea
                value={clientNote}
                onChange={(e) => setClientNote(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-purple-500 min-h-[90px]"
                placeholder="Anything the owner should know?"
              />
            </div>

            <div>
              <div className="text-sm font-semibold text-gray-700 mb-2">Meeting type</div>
              <div className="flex flex-wrap gap-2">
                {providerOptions.map((option) => {
                  const isAvailable = availableProviders.includes(option.key);
                  const isActive = meetingProvider === option.key;
                  return (
                    <button
                      key={option.key}
                      onClick={() => isAvailable && setMeetingProvider(option.key)}
                      disabled={!isAvailable}
                      className={`px-3 py-2 rounded-2xl text-sm font-semibold border transition-colors ${
                        isActive
                          ? 'border-purple-600 bg-purple-600 text-white'
                          : 'border-gray-200 bg-white text-gray-700 hover:border-purple-400'
                      } ${!isAvailable ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      {option.label}
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Choose whether the meeting should be created as a Google Meet or Microsoft Teams session.
                We automatically prioritize the provider that is connected for the owner.
              </p>
            </div>

            {/* Manual Meeting Link Option */}
            <div className="border-t border-gray-200 pt-4 space-y-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="useManualLink"
                  checked={useManualLink}
                  onChange={(e) => {
                    setUseManualLink(e.target.checked);
                    if (!e.target.checked) {
                      setManualMeetingLink('');
                    }
                  }}
                  className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
                />
                <label htmlFor="useManualLink" className="text-sm font-semibold text-gray-700 cursor-pointer">
                  Use manual meeting link (if automatic creation fails)
                </label>
              </div>
              
              {useManualLink && (
                <div className="space-y-2 animate-in fade-in slide-in-from-top-2">
                  <label className="block text-sm font-semibold text-gray-700">
                    Meeting Link (Google Meet or Microsoft Teams)
                  </label>
                  <input
                    type="url"
                    value={manualMeetingLink}
                    onChange={(e) => setManualMeetingLink(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="https://meet.google.com/xxx-xxxx-xxx or https://teams.microsoft.com/..."
                  />
                  <p className="text-xs text-gray-500">
                    Paste your Google Meet or Microsoft Teams link here. The system will try to create one automatically, but you can provide your own if needed.
                  </p>
                </div>
              )}
            </div>

            <button
              onClick={submitBooking}
              disabled={bookingSubmitting || !clientName.trim() || !clientEmail.includes('@')}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-4 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-lg shadow-lg hover:shadow-xl"
            >
              {bookingSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <LoadingSpinner size="sm" />
                  Creating meeting...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Book Meeting & Create Calendar Event
                </span>
              )}
            </button>
            <p className="text-xs text-gray-500 text-center">
              A Google Meet or Microsoft Teams link will be automatically created
            </p>
          </div>
        )}

        {/* Success */}
        {booking && (
          <div id="booking-success" className="bg-gradient-to-br from-green-50 to-purple-50 border-2 border-green-500 rounded-2xl shadow-lg p-6 space-y-4 animate-in fade-in slide-in-from-bottom-4">
            <div className="flex items-center gap-3">
              <div className="bg-green-500 rounded-full p-2">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900">Meeting Booked Successfully!</h2>
            </div>
            
            <div className="bg-white rounded-xl p-4 space-y-3 border border-gray-200">
              <div className="flex items-start gap-2">
                <svg className="w-5 h-5 text-purple-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <div>
                  <p className="text-sm text-gray-600">Confirmation ID</p>
                  <p className="text-lg font-bold text-gray-900">#{booking.booking_id}</p>
                </div>
              </div>
              
              <div className="flex items-start gap-2">
                <svg className="w-5 h-5 text-purple-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <div>
                  <p className="text-sm text-gray-600">Scheduled Time</p>
                  <p className="text-lg font-bold text-gray-900">
                    {new Date(booking.start_time).toLocaleString('en-US', { 
                      weekday: 'long', 
                      year: 'numeric', 
                      month: 'long', 
                      day: 'numeric',
                      hour: 'numeric',
                      minute: '2-digit'
                    })}
                  </p>
                </div>
              </div>
              
              {booking.meeting_link && (
                <div className="flex items-start gap-2 pt-2 border-t border-gray-200">
                  <svg className="w-5 h-5 text-purple-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <div className="flex-1">
                    <p className="text-sm text-gray-600 mb-2">Meeting Link</p>
                    <a 
                      className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white font-semibold px-4 py-2 rounded-lg transition-colors" 
                      href={booking.meeting_link} 
                      target="_blank" 
                      rel="noreferrer"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                      Join Meeting
                    </a>
                  </div>
                </div>
              )}
            </div>
            
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <p className="text-sm text-blue-800">
                <span className="font-semibold">✓</span> Calendar event created in owner's calendar
                {booking.meeting_link && ' • Meeting link generated'}
                {' • '}Confirmation email sent (if configured)
              </p>
            </div>
            
            <button
              onClick={() => {
                setBooking(null);
                setSelectedSlot(null);
                setClientName('');
                setClientEmail('');
                setClientNote('');
              }}
              className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-2 rounded-lg transition-colors"
            >
              Book Another Meeting
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default PublicBookingPage;


