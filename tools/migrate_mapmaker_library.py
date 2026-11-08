"""Add only the personal map library table. Run with the deployment's app config."""

from vtt import create_app
from vtt.extensions import db
from vtt.models.mapmaker_project import MapmakerProject


def migrate(app):
    with app.app_context():
        MapmakerProject.__table__.create(bind=db.engine, checkfirst=True)
        return "mapmaker_projects ready"


if __name__ == "__main__":
    print(migrate(create_app()))
