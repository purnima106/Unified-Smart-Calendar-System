from flask import Flask, jsonify
from flask_cors import CORS
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from config import Config
from models.user_model import db, User
from models.calendar_connection_model import CalendarConnection
from controllers.auth_controller import auth_bp
from controllers.calendar_controller import calendar_bp
from datetime import datetime

def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize Flask-Session
    Session(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    # Remove the login_view since we're handling login via API endpoints
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Initialize CORS
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(calendar_bp, url_prefix='/api/calendar')
    
    # Google OAuth callback redirect (Google calls /oauth2callback by default)
    @app.route('/oauth2callback')
    def google_oauth_callback():
        """Redirect Google OAuth callback to our actual handler"""
        from flask import request, redirect
        return redirect(f'/api/auth/google/callback?{request.query_string.decode()}')
    
    # Google OAuth callback redirect (Google calls /auth/google/callback by default)
    @app.route('/auth/google/callback')
    def google_oauth_callback_alt():
        """Redirect Google OAuth callback to our actual handler"""
        from flask import request, redirect
        return redirect(f'/api/auth/google/callback?{request.query_string.decode()}')
    
    # Microsoft OAuth callback redirect (Microsoft calls /outlook_callback by default)
    @app.route('/outlook_callback')
    def microsoft_oauth_callback():
        """Redirect Microsoft OAuth callback to our actual handler"""
        from flask import request, redirect
        return redirect(f'/api/auth/microsoft/callback?{request.query_string.decode()}')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        try:
            # Test database connection
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            db_status = 'healthy'
        except Exception as e:
            db_status = f'unhealthy: {str(e)}'
        
        # Check OAuth configuration
        oauth_status = {}
        microsoft_enabled = app.config.get('MICROSOFT_ENABLED', False)
        
        try:
            from services.google_service import GoogleCalendarService
            GoogleCalendarService()
            oauth_status['google'] = 'configured'
        except Exception as e:
            oauth_status['google'] = f'not configured: {str(e)}'
        
        if microsoft_enabled:
            try:
                from services.microsoft_service import MicrosoftCalendarService
                MicrosoftCalendarService()
                oauth_status['microsoft'] = 'configured'
            except Exception as e:
                oauth_status['microsoft'] = f'not configured: {str(e)}'
        else:
            oauth_status['microsoft'] = 'disabled (temporarily)'
        
        return jsonify({
            'status': 'healthy',
            'message': 'Unified Smart Calendar System API is running',
            'database': db_status,
            'oauth_configuration': oauth_status,
            'microsoft_enabled': microsoft_enabled,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Root endpoint
    @app.route('/')
    def root():
        return jsonify({
            'message': 'Unified Smart Calendar System API',
            'version': '1.0.0',
            'endpoints': {
                'health': '/health',
                'auth': '/api/auth',
                'calendar': '/api/calendar'
            }
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
