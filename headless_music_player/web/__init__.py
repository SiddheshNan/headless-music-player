"""HTTP layer: thin handlers that validate input, send commands to the engine and return state."""

import logging
from concurrent.futures import TimeoutError as FutureTimeout

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from ..engine import CommandError
from .api import api
from .validate import ApiError
from .views import views

logger = logging.getLogger(__name__)


def register(app: Flask) -> None:
    app.register_blueprint(api)
    app.register_blueprint(views)

    @app.errorhandler(ApiError)
    @app.errorhandler(CommandError)
    def command_error(e):
        return jsonify({"error": str(e)}), e.status

    @app.errorhandler(FutureTimeout)
    def busy(e):
        return jsonify({"error": "The player is busy. Try again."}), 503

    @app.errorhandler(HTTPException)
    def http_error(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": e.description}), e.code
        return e

    @app.errorhandler(Exception)
    def unexpected(e):
        logger.exception("Unhandled error")
        if request.path.startswith("/api/"):
            return jsonify({"error": "Something went wrong. See the server log."}), 500
        return "Something went wrong. See the server log.", 500
