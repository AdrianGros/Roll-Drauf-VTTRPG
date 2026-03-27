from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity
import pyotp

from .models import User
from .extensions import db, limiter

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@bp.route('/register', methods=['POST'])
@limiter.limit('10 per hour')
def api_register():
    data = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'username, email, password required'}), 400

    existing = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing:
        return jsonify({'error': 'username or email already exists'}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify(user.serialize()), 201


@bp.route('/login', methods=['POST'])
@limiter.limit('5 per minute')
def api_login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    otp = data.get('otp')

    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'invalid credentials'}), 401

    if user.mfa_enabled:
        if not otp:
            return jsonify({'error': 'mfa_required'}), 401
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(otp):
            return jsonify({'error': 'invalid_mfa_code'}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({'access_token': access_token, 'user': user.serialize()})


@bp.route('/me', methods=['GET'])
@jwt_required()
def api_me():
    user_identity = get_jwt_identity()
    try:
        user_id = int(user_identity)
    except (TypeError, ValueError):
        return jsonify({'error': 'invalid token identity'}), 422

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'user not found'}), 404

    return jsonify(user.serialize())


@bp.route('/mfa/setup', methods=['POST'])
@jwt_required()
def api_mfa_setup():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'user not found'}), 404

    if not user.mfa_secret:
        user.mfa_secret = pyotp.random_base32()
        db.session.commit()

    totp = pyotp.TOTP(user.mfa_secret)
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name='roll drauf vtt')
    return jsonify({'mfa_enabled': user.mfa_enabled, 'provisioning_uri': provisioning_uri})


@bp.route('/mfa/verify', methods=['POST'])
@jwt_required()
def api_mfa_verify():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'user not found'}), 404

    data = request.get_json() or {}
    otp = data.get('otp')
    if not otp:
        return jsonify({'error': 'otp required'}), 400

    if not user.mfa_secret:
        return jsonify({'error': 'mfa_not_setup'}), 400

    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(otp):
        return jsonify({'error': 'invalid_mfa_code'}), 401

    user.mfa_enabled = True
    db.session.commit()

    return jsonify({'mfa_enabled': True})
