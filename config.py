# roll drauf vtt backend configuration

import os

class Config:
    """Base configuration"""
    APP_NAME = "roll drauf vtt"
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'

    # M17: Platform & Profile Tier Configuration
    PLATFORM_ROLES = {
        'owner': {'level': 100, 'description': 'Platform owner'},
        'admin': {'level': 80, 'description': 'Full admin access'},
        'moderator': {'level': 60, 'description': 'Content & user moderation'},
        'supporter': {'level': 40, 'description': 'Support team access'}
    }

    PROFILE_TIERS = {
        'listener': {
            'storage_quota_gb': 0,
            'active_campaigns': 0,
            'description': 'Observer only'
        },
        'player': {
            'storage_quota_gb': 0,
            'active_campaigns': 0,
            'description': 'Can join campaigns'
        },
        'dm': {
            'storage_quota_gb': 1,
            'active_campaigns': 3,
            'description': 'Content creator (Dungeonmaster)'
        },
        'headmaster': {
            'storage_quota_gb': 5,
            'active_campaigns': 5,
            'description': 'Senior content creator (Headmaster)'
        }
    }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Must be set in production

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
