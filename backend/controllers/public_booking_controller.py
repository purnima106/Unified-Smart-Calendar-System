from flask import Blueprint, request, jsonify

from services.public_booking_service import PublicBookingService
from services.booking_service import BookingService


public_bp = Blueprint("public", __name__)


@public_bp.route("/slots/<string:username>", methods=["GET"])
def get_public_slots(username: str):
    """
    Public endpoint: returns ONLY available slots (no private details).
    Query params:
      - start: ISO datetime
      - end: ISO datetime
      - duration_minutes: 30 or 60
    """
    try:
        start = request.args.get("start")
        end = request.args.get("end")
        duration_minutes = int(request.args.get("duration_minutes", "30"))
        if not start or not end:
            return jsonify({"error": "start and end query params are required"}), 400

        data = PublicBookingService.get_slots(username, start, end, duration_minutes)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@public_bp.route("/book", methods=["POST"])
def create_public_booking():
    """
    Public endpoint: create a booking.
    Body:
      - username
      - client_name
      - client_email
      - client_note (optional)
      - start_time (ISO)
      - end_time (ISO)
      - duration_minutes (30/60)
      - manual_meeting_link (optional) - if provided, uses this instead of auto-creating
    """
    try:
        payload = request.get_json() or {}
        print(f"Received booking request: {payload}")
        result = BookingService.create_public_booking(payload)
        print(f"Booking created successfully: {result}")
        return jsonify({"status": "success", "booking": result})
    except Exception as e:
        msg = str(e)
        print(f"Booking error: {msg}")
        import traceback
        traceback.print_exc()
        if "no longer available" in msg.lower():
            return jsonify({"status": "error", "error": "slot_no_longer_available"}), 409
        return jsonify({"status": "error", "error": msg}), 400


