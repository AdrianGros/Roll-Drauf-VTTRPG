#!/usr/bin/env python
"""
M18: Scheduled job to hard-delete users after 30-day grace period.

Run daily at 2am (off-peak time).

Usage:
    python jobs/delete_marked_users_job.py
    # Or in crontab: 0 2 * * * /path/to/delete_marked_users_job.py
"""

import logging
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/user_deletion_job.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_job():
    """Execute the hard-delete job."""
    try:
        from vtt_app import create_app
        from vtt_app.utils.user_deletion import delete_marked_users_after_grace_period
        from vtt_app.models import User

        app = create_app(config_name='production')

        with app.app_context():
            logger.info('Starting user hard-delete job...')

            # Get system admin for logging (first admin user)
            admin = User.query.filter_by(platform_role='admin').first()

            # Run hard-delete
            result = delete_marked_users_after_grace_period(admin_user=admin)

            # Log result
            logger.info(f'Job completed successfully.')
            logger.info(f'  Deleted users: {result["deleted_count"]}')
            logger.info(f'  Errors: {len(result["errors"])}')

            if result['errors']:
                for error in result['errors']:
                    logger.error(f'    User {error["user_id"]}: {error["error"]}')

            # Metrics
            logger.info(f'Execution time: {datetime.now().isoformat()}')

            return result

    except Exception as e:
        logger.error(f'Job failed with error: {e}', exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    result = run_job()
    sys.exit(0 if result['errors'] == 0 else 1)
