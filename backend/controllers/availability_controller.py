from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from services.availability_service import AvailabilityService


availability_bp = Blueprint("availability", __name__)


@availability_bp.route("", methods=["GET"])
@login_required
def get_my_availability():
    try:
        data = AvailabilityService.get_owner_availability(current_user.id)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@availability_bp.route("", methods=["POST"])
@login_required
def set_my_availability():
    try:
        payload = request.get_json() or {}
        data = AvailabilityService.set_owner_availability(current_user.id, payload)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


