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
  const [booking, setBooking] = useState(null);
  const [bookingSubmitting, setBookingSubmitting] = useState(false);

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
      title: 'Available',
      start: s.start_time,
      end: s.end_time,
      backgroundColor: '#7c3aed',
      borderColor: '#6d28d9',
      textColor: '#ffffff',
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
    setSelectedSlot({
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      duration_minutes: duration,
    });
    setBooking(null);
  };

  const submitBooking = async () => {
    if (!selectedSlot) return;
    if (!clientName.trim()) return setError('Please enter your name');
    if (!clientEmail.includes('@')) return setError('Please enter a valid email');

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
      };
      const res = await publicBookingAPI.book(payload);
      setBooking(res.data.booking);
      setSelectedSlot(null);
      await loadSlots(defaultRange);
    } catch (e) {
      const status = e.response?.status;
      if (status === 409) {
        setError('Slot no longer available. Please pick another time.');
        await loadSlots(defaultRange);
      } else {
        setError(e.response?.data?.error || e.message || 'Booking failed');
      }
    } finally {
      setBookingSubmitting(false);
    }
  };

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
          <div className="bg-white border border-gray-200 rounded-2xl shadow-sm p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">Confirm your details</h2>
              <button
                onClick={() => setSelectedSlot(null)}
                className="text-sm font-semibold text-gray-500 hover:text-gray-700"
              >
                Cancel
              </button>
            </div>

            <div className="text-sm text-gray-600">
              Selected slot: <span className="font-semibold text-gray-900">{new Date(selectedSlot.start_time).toLocaleString()}</span>
              {' '}({selectedSlot.duration_minutes} min)
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
                  onChange={(e) => setClientEmail(e.target.value)}
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

            <button
              onClick={submitBooking}
              disabled={bookingSubmitting}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-3 rounded-xl transition-colors disabled:opacity-50"
            >
              {bookingSubmitting ? 'Booking...' : 'Book meeting'}
            </button>
          </div>
        )}

        {/* Success */}
        {booking && (
          <div className="bg-white border border-gray-200 rounded-2xl shadow-sm p-6 space-y-2">
            <h2 className="text-xl font-bold text-gray-900">Booked!</h2>
            <p className="text-gray-700 text-sm">
              Confirmation: <span className="font-semibold">#{booking.booking_id}</span>
            </p>
            <p className="text-gray-700 text-sm">
              When: <span className="font-semibold">{new Date(booking.start_time).toLocaleString()}</span>
            </p>
            {booking.meeting_link && (
              <p className="text-gray-700 text-sm">
                Meeting link:{' '}
                <a className="text-purple-700 font-semibold hover:underline" href={booking.meeting_link} target="_blank" rel="noreferrer">
                  Open
                </a>
              </p>
            )}
            <p className="text-gray-500 text-xs">
              You’ll also receive a confirmation email (if email is configured).
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PublicBookingPage;


