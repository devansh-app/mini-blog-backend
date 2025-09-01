"""
Error handlers for centralized error handling
"""

from flask import jsonify
from app.core.error_codes import ErrorMessages, ErrorCodes


def handle_validation_error(error):
    """Handle validation errors"""
    return jsonify(ErrorMessages.get_error_response(ErrorCodes.BAD_REQUEST, str(error))), 400


def handle_database_error(error):
    """Handle database errors"""
    return jsonify(ErrorMessages.get_error_response(ErrorCodes.DATABASE_ERROR, str(error))), 500


def handle_generic_error(error):
    """Handle generic errors"""
    return jsonify(ErrorMessages.get_error_response(ErrorCodes.INTERNAL_SERVER_ERROR, str(error))), 500


def register_error_handlers(app):
    """Register all error handlers with the Flask app"""
    app.register_error_handler(400, handle_validation_error)
    app.register_error_handler(500, handle_generic_error)
