#!/usr/bin/env python
"""M27/M28: Background job - cleanup soft-deleted assets after retention period."""

import logging
from datetime import datetime, timedelta
from vtt_app import create_app
from vtt_app.extensions import db
from vtt_app.models import Asset, AuditLog
from vtt_app.utils.time import utcnow
from vtt_app.storage import get_storage_adapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RETENTION_DAYS = 7  # M28: Keep soft-deleted assets for 7 days


def cleanup_soft_deleted_assets():
    """Delete soft-deleted assets after 7-day retention period."""
    app = create_app(config_name='production')

    with app.app_context():
        cutoff = utcnow() - timedelta(days=RETENTION_DAYS)
        assets = Asset.query.filter(
            Asset.deleted_at < cutoff,
            Asset.deleted_at != None
        ).all()

        storage = get_storage_adapter()
        deleted_count = 0
        errors = []

        for asset in assets:
            try:
                # Delete from storage
                storage.delete(asset.storage_key)

                # Log retention action
                log = AuditLog(
                    user_id=asset.uploaded_by,
                    action='asset_permanently_deleted',
                    resource_type='asset',
                    resource_id=asset.id,
                    details={
                        'reason': 'retention_period_expired',
                        'retention_days': RETENTION_DAYS,
                        'deleted_at': asset.deleted_at.isoformat(),
                    },
                    timestamp=utcnow()
                )
                db.session.add(log)

                # Delete from DB
                db.session.delete(asset)
                deleted_count += 1

            except Exception as e:
                logger.error(f'Error deleting asset {asset.id}: {e}')
                errors.append({'asset_id': asset.id, 'error': str(e)})

        db.session.commit()
        logger.info(f'Cleanup complete: deleted {deleted_count} assets, {len(errors)} errors')
        return {'deleted_count': deleted_count, 'errors': errors}


if __name__ == '__main__':
    result = cleanup_soft_deleted_assets()
