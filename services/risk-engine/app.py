"""
Flask application factory for precise-risk-engine-api microservice.

Configured for port 8004 with PostgreSQL and Redis integration.
"""
import os
import logging
from flask import Flask
from flask_cors import CORS
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize extensions
cache = Cache()
db = SQLAlchemy()


def create_app(config_name: str = None) -> Flask:
    """
    Application factory for precise-risk-engine-api.

    Args:
        config_name: Configuration environment (development, testing, production)

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)

    # Load configuration
    config_name = config_name or os.getenv("FLASK_ENV", "development")
    load_config(app, config_name)

    # Initialize extensions
    cache.init_app(app)
    db.init_app(app)
    CORS(app)

    # Import blueprints after app is created
    from routes.scoring import scoring_bp
    from routes.rules import rules_bp
    from routes.feedback import feedback_bp
    from routes.metrics import metrics_bp

    # Register blueprints
    app.register_blueprint(scoring_bp, url_prefix="/api/v1/scoring")
    app.register_blueprint(rules_bp, url_prefix="/api/v1/rules")
    app.register_blueprint(feedback_bp, url_prefix="/api/v1/feedback")
    app.register_blueprint(metrics_bp, url_prefix="/api/v1/metrics")

    # Initialize PreciseRiskModel (config-driven with ML integration)
    with app.app_context():
        try:
            # Make sure the current directory is in the path
            import sys
            app_dir = os.path.dirname(os.path.abspath(__file__))
            if app_dir not in sys.path:
                sys.path.insert(0, app_dir)

            # Try import with debuggin
            logger.info(f"Python path: {sys.path[:3]}")
            logger.info(f"App directory: {app_dir}")

            from models.risk_model import PreciseRiskModel

            risk_model = PreciseRiskModel()
            risk_model.load_config()
            logger.info(f"PreciseRiskModel loaded with {len(risk_model.factors)} factors")

            # Load ML models
            if risk_model.load_ml_models():
                logger.info("ML models loaded successfully")
            else:
                logger.warning("ML models not available, using rule-based scoring only")

            app.risk_model = risk_model
        except Exception as e:
            logger.error(f"Failed to load PreciseRiskModel: {e}")
            import traceback
            traceback.print_exc()
            # Continue without model loading to allow health checks
            app.risk_model = None

    # Health check endpoint
    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint for orchestration."""
        factors_count = 0
        if hasattr(app, "risk_model") and app.risk_model is not None:
            factors_count = len(app.risk_model.factors)

        return {
            "status": "healthy",
            "service": "precise-risk-engine-api",
            "port": app.config.get("PORT", 8004),
            "factors": factors_count,
        }, 200

    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request."""
        return {"error": "Bad Request", "message": str(error)}, 400

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found."""
        return {"error": "Not Found", "message": "Endpoint not found"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error."""
        logger.error(f"Internal server error: {error}")
        return {
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }, 500

    logger.info(f"Flask app created in {config_name} mode")
    return app


def load_config(app: Flask, config_name: str):
    """
    Load configuration based on environment.

    Args:
        app: Flask application instance
        config_name: Configuration environment name
    """
    app.config["PORT"] = int(os.getenv("PORT", 8004))

    # Database configuration
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "cbp_sentry")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "password")

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Redis configuration
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = os.getenv("REDIS_PORT", "6379")
    app.config["CACHE_TYPE"] = "redis"
    app.config["CACHE_REDIS_URL"] = f"redis://{redis_host}:{redis_port}/0"

    # Model configuration
    app.config["MODEL_CONFIG_PATH"] = os.getenv(
        "MODEL_CONFIG_PATH",
        "/home/rahulvadera/cbp-sentry/services/risk-engine/config/cbp.yaml"
    )

    # Flask configuration
    if config_name == "testing":
        app.config["TESTING"] = True
        app.config["CACHE_TYPE"] = "simple"  # Use simple cache for testing
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    elif config_name == "production":
        app.config["TESTING"] = False
        app.config["JSON_SORT_KEYS"] = False
    else:  # development
        app.config["TESTING"] = False
        app.config["DEBUG"] = True

    logger.info(f"Configuration loaded for {config_name} environment")
