"""
Role model for RBAC (Role-Based Access Control).
"""

from vtt_app.extensions import db


class Role(db.Model):
    """Role entity (Player, DM, Admin)."""

    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    users = db.relationship('User', backref='role', lazy=True)

    def __repr__(self):
        return f'<Role {self.name}>'

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }


# Bootstrap default roles
def init_default_roles(db_session):
    """Create default roles if they don't exist."""
    roles_to_create = [
        {'name': 'Player', 'description': 'Can join campaigns, roll dice, move tokens'},
        {'name': 'DM', 'description': 'Can create campaigns, manage maps, invite players'},
        {'name': 'Admin', 'description': 'Full server access, user management, moderation'}
    ]

    for role_data in roles_to_create:
        if not Role.query.filter_by(name=role_data['name']).first():
            role = Role(name=role_data['name'], description=role_data['description'])
            db_session.add(role)

    db_session.commit()
