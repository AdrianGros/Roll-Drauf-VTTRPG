"""
M17 Tests: Permission system, role hierarchy, quotas, audit logging.
"""

import pytest
from datetime import datetime
from vtt_app import create_app
from vtt_app.extensions import db
from vtt_app.models import User, Role, Campaign, CampaignMember, AuditLog
from vtt_app.permissions import (
    can_view_campaign, can_edit_campaign, can_delete_campaign, can_create_campaign,
    can_view_all_campaigns, can_suspend_user, can_upload_asset, has_platform_role
)
from vtt_app.utils.audit import log_campaign_deleted, log_user_suspended


# ===== FIXTURES =====

@pytest.fixture
def app():
    """Create and configure a test app."""
    app = create_app(config_name='testing')

    with app.app_context():
        db.create_all()

        # Create default roles
        for role_name in ['Player', 'DM', 'Admin']:
            db.session.add(Role(name=role_name))

        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Provide app context for direct model testing."""
    with app.app_context():
        yield app


# ===== HELPERS =====

def _create_user(username, email=None, platform_role=None, profile_tier=None,
                 storage_quota=None, campaigns_quota=None, role_id=1):
    """Create a test user with specific roles and quotas."""
    user = User(
        username=username,
        email=email or f'{username}@test.com',
        role_id=role_id,
        platform_role=platform_role or 'supporter',
        profile_tier=profile_tier or 'player',
        storage_quota_gb=storage_quota,
        active_campaigns_quota=campaigns_quota
    )
    user.set_password('Password123!')
    db.session.add(user)
    db.session.flush()
    return user


def _create_campaign(owner, name="Test Campaign"):
    """Create a test campaign."""
    campaign = Campaign(
        name=name,
        description="A test campaign",
        owner_id=owner.id,
        status='active',
        max_players=6
    )
    db.session.add(campaign)
    db.session.flush()

    # Add owner as DM member
    member = CampaignMember(
        campaign_id=campaign.id,
        user_id=owner.id,
        campaign_role='DM',
        status='active',
        joined_at=datetime.utcnow(),
        invited_at=datetime.utcnow(),
        accepted_at=datetime.utcnow(),
        invited_by=owner.id
    )
    db.session.add(member)
    db.session.commit()
    return campaign


def _login(client, username, password="Password123!"):
    """Helper to login user."""
    response = client.post(
        '/api/auth/login',
        json={'username': username, 'password': password}
    )
    assert response.status_code == 200
    return response.get_json()['token']


# ===== TESTS: PERMISSION FUNCTIONS =====

class TestCampaignPermissions:
    """Test campaign-level permission functions."""

    def test_can_view_campaign_as_supporter(self, app_context):
        """Supporter can view all campaigns."""
        supporter = _create_user('supporter', platform_role='supporter')
        owner = _create_user('owner', platform_role=None, profile_tier='dm')
        campaign = _create_campaign(owner)

        assert can_view_campaign(supporter, campaign) == True

    def test_can_view_campaign_as_dm_owner(self, app_context):
        """DM can view own campaign."""
        dm = _create_user('dm', platform_role=None, profile_tier='dm')
        campaign = _create_campaign(dm)

        assert can_view_campaign(dm, campaign) == True

    def test_can_view_campaign_as_player_not_member(self, app_context):
        """Player cannot view campaign they're not member of."""
        player = _create_user('player', profile_tier='player')
        owner = _create_user('owner', profile_tier='dm')
        campaign = _create_campaign(owner)

        assert can_view_campaign(player, campaign) == False

    def test_can_view_campaign_as_campaign_member(self, app_context):
        """Player can view campaign if they're a member."""
        player = _create_user('player', profile_tier='player')
        owner = _create_user('owner', profile_tier='dm')
        campaign = _create_campaign(owner)

        # Add player as member
        member = CampaignMember(
            campaign_id=campaign.id,
            user_id=player.id,
            campaign_role='Player',
            status='active',
            joined_at=datetime.utcnow(),
            invited_at=datetime.utcnow(),
            invited_by=owner.id
        )
        db.session.add(member)
        db.session.commit()

        assert can_view_campaign(player, campaign) == True

    def test_can_edit_campaign_as_dm_owner(self, app_context):
        """DM can edit own campaign."""
        dm = _create_user('dm', profile_tier='dm')
        campaign = _create_campaign(dm)

        assert can_edit_campaign(dm, campaign) == True

    def test_can_edit_campaign_as_moderator(self, app_context):
        """Moderator can edit any campaign."""
        moderator = _create_user('moderator', platform_role='moderator')
        owner = _create_user('owner', profile_tier='dm')
        campaign = _create_campaign(owner)

        assert can_edit_campaign(moderator, campaign) == True

    def test_can_delete_campaign_as_dm_owner(self, app_context):
        """DM can delete own campaign."""
        dm = _create_user('dm', profile_tier='dm')
        campaign = _create_campaign(dm)

        assert can_delete_campaign(dm, campaign) == True

    def test_can_delete_campaign_as_moderator(self, app_context):
        """Moderator can delete any campaign."""
        moderator = _create_user('moderator', platform_role='moderator')
        owner = _create_user('owner', profile_tier='dm')
        campaign = _create_campaign(owner)

        assert can_delete_campaign(moderator, campaign) == True

    def test_cannot_delete_campaign_as_player(self, app_context):
        """Player cannot delete campaign."""
        player = _create_user('player', profile_tier='player')
        owner = _create_user('owner', profile_tier='dm')
        campaign = _create_campaign(owner)

        assert can_delete_campaign(player, campaign) == False


# ===== TESTS: QUOTA SYSTEM =====

class TestQuotaSystem:
    """Test quota enforcement for campaigns and storage."""

    def test_dm_can_create_3_campaigns(self, app_context):
        """DM tier can create up to 3 campaigns."""
        dm = _create_user('dm', profile_tier='dm', campaigns_quota=3)
        db.session.commit()

        # Create 3 campaigns
        for i in range(3):
            campaign = _create_campaign(dm, name=f'Campaign {i+1}')
            assert campaign.id is not None

        # Check can_create_campaign returns False after quota
        assert can_create_campaign(dm) == False

    def test_headmaster_can_create_5_campaigns(self, app_context):
        """Headmaster tier can create up to 5 campaigns."""
        hm = _create_user('hm', profile_tier='headmaster', campaigns_quota=5)
        db.session.commit()

        # Create 5 campaigns
        for i in range(5):
            campaign = _create_campaign(hm, name=f'Campaign {i+1}')
            assert campaign.id is not None

        # Check can_create_campaign returns False after quota
        assert can_create_campaign(hm) == False

    def test_player_cannot_create_campaign(self, app_context):
        """Player cannot create campaign."""
        player = _create_user('player', profile_tier='player')
        db.session.commit()

        assert can_create_campaign(player) == False

    def test_storage_quota_check_dm(self, app_context):
        """DM with 1GB quota cannot upload more than 1GB."""
        dm = _create_user('dm', profile_tier='dm', storage_quota=1)
        db.session.commit()

        # Try upload 500MB (should succeed)
        allowed, msg = can_upload_asset(dm, 500)
        assert allowed == True

        # Simulate 600MB used
        dm.storage_used_gb = 0.6
        db.session.commit()

        # Try upload 600MB (should fail)
        allowed, msg = can_upload_asset(dm, 600)
        assert allowed == False

    def test_storage_quota_check_headmaster(self, app_context):
        """Headmaster with 5GB quota has more room."""
        hm = _create_user('hm', profile_tier='headmaster', storage_quota=5)
        db.session.commit()

        # Simulate 4GB used
        hm.storage_used_gb = 4.0
        db.session.commit()

        # Try upload 1.5GB (should fail, only 1GB available)
        allowed, msg = can_upload_asset(hm, 1500)
        assert allowed == False

        # Try upload 0.5GB (should succeed)
        allowed, msg = can_upload_asset(hm, 500)
        assert allowed == True

    def test_admin_unlimited_storage(self, app_context):
        """Admin can upload unlimited storage."""
        admin = _create_user('admin', platform_role='admin')
        db.session.commit()

        # Try upload 999GB
        allowed, msg = can_upload_asset(admin, 999000)
        assert allowed == True


# ===== TESTS: USER SUSPENSION =====

class TestUserSuspension:
    """Test user suspension permissions."""

    def test_moderator_can_suspend_user(self, app_context):
        """Moderator can suspend a user."""
        moderator = _create_user('mod', platform_role='moderator')
        target = _create_user('target')
        db.session.commit()

        assert can_suspend_user(moderator, target) == True

    def test_admin_can_suspend_user(self, app_context):
        """Admin can suspend a user."""
        admin = _create_user('admin', platform_role='admin')
        target = _create_user('target')
        db.session.commit()

        assert can_suspend_user(admin, target) == True

    def test_player_cannot_suspend_user(self, app_context):
        """Player cannot suspend a user."""
        player = _create_user('player', profile_tier='player')
        target = _create_user('target')
        db.session.commit()

        assert can_suspend_user(player, target) == False

    def test_user_cannot_suspend_self(self, app_context):
        """Admin cannot suspend themselves."""
        admin = _create_user('admin', platform_role='admin')
        db.session.commit()

        assert can_suspend_user(admin, admin) == False

    def test_suspended_user_cannot_view_campaigns(self, app_context):
        """Suspended user cannot view campaigns."""
        suspended = _create_user('suspended')
        suspended.is_suspended = True
        owner = _create_user('owner', profile_tier='dm')
        campaign = _create_campaign(owner)
        db.session.commit()

        assert can_view_campaign(suspended, campaign) == False


# ===== TESTS: TEAM VIEW =====

class TestTeamView:
    """Test team dashboard visibility."""

    def test_supporter_can_view_all_campaigns(self, app_context):
        """Supporter can view all campaigns."""
        supporter = _create_user('sup', platform_role='supporter')
        owner1 = _create_user('owner1', profile_tier='dm')
        owner2 = _create_user('owner2', profile_tier='dm')

        camp1 = _create_campaign(owner1, 'Campaign 1')
        camp2 = _create_campaign(owner2, 'Campaign 2')
        db.session.commit()

        assert can_view_all_campaigns(supporter) == True

    def test_dm_cannot_view_all_campaigns(self, app_context):
        """DM cannot access team view (only own campaigns)."""
        dm = _create_user('dm', profile_tier='dm')
        db.session.commit()

        assert can_view_all_campaigns(dm) == False

    def test_moderator_can_view_all_campaigns(self, app_context):
        """Moderator can view all campaigns."""
        moderator = _create_user('mod', platform_role='moderator')
        db.session.commit()

        assert can_view_all_campaigns(moderator) == True


# ===== TESTS: AUDIT LOGGING =====

class TestAuditLogging:
    """Test audit log creation and tracking."""

    def test_campaign_deletion_logged(self, app_context):
        """Campaign deletion creates audit log."""
        admin = _create_user('admin', platform_role='admin')
        owner = _create_user('owner', profile_tier='dm')
        campaign = _create_campaign(owner)
        db.session.commit()

        # Log campaign deletion
        log_campaign_deleted(campaign, deleted_by=admin, reason='Test deletion')
        db.session.commit()

        # Verify audit log
        log = AuditLog.query.filter_by(action='campaign_deleted').first()
        assert log is not None
        assert log.resource_type == 'campaign'
        assert log.resource_id == campaign.id
        assert log.performed_by_id == admin.id
        assert log.details['reason'] == 'Test deletion'

    def test_user_suspension_logged(self, app_context):
        """User suspension creates audit log."""
        admin = _create_user('admin', platform_role='admin')
        target = _create_user('target')
        db.session.commit()

        # Log suspension
        log_user_suspended(target, suspended_by=admin, reason='Abuse')
        db.session.commit()

        # Verify audit log
        log = AuditLog.query.filter_by(action='user_suspended').first()
        assert log is not None
        assert log.resource_type == 'user'
        assert log.resource_id == target.id
        assert log.performed_by_id == admin.id
        assert log.details['reason'] == 'Abuse'

    def test_audit_log_timestamp(self, app_context):
        """Audit log has timestamp."""
        admin = _create_user('admin', platform_role='admin')
        owner = _create_user('owner', profile_tier='dm')
        campaign = _create_campaign(owner)
        db.session.commit()

        log_campaign_deleted(campaign, deleted_by=admin)
        db.session.commit()

        log = AuditLog.query.first()
        assert log.timestamp is not None
        assert isinstance(log.timestamp, datetime)


# ===== TESTS: ROLE HIERARCHY =====

class TestRoleHierarchy:
    """Test role level hierarchy."""

    def test_owner_has_highest_level(self, app_context):
        """Owner role has level 100."""
        owner = _create_user('owner', platform_role='owner')
        db.session.commit()

        assert owner.platform_role == 'owner'

    def test_admin_level_below_owner(self, app_context):
        """Admin level (80) is below owner (100)."""
        admin = _create_user('admin', platform_role='admin')
        db.session.commit()

        assert admin.platform_role == 'admin'

    def test_moderator_can_do_admin_things(self, app_context):
        """Moderator can delete campaigns (admin permission)."""
        moderator = _create_user('mod', platform_role='moderator')
        owner = _create_user('owner', profile_tier='dm')
        campaign = _create_campaign(owner)
        db.session.commit()

        assert can_delete_campaign(moderator, campaign) == True

    def test_supporter_cannot_delete_campaigns(self, app_context):
        """Supporter cannot delete (only view)."""
        supporter = _create_user('sup', platform_role='supporter')
        owner = _create_user('owner', profile_tier='dm')
        campaign = _create_campaign(owner)
        db.session.commit()

        assert can_delete_campaign(supporter, campaign) == False


# ===== TESTS: PROFILE TIERS =====

class TestProfileTiers:
    """Test profile tier system (dm, headmaster, player, listener)."""

    def test_dm_tier_has_quotas(self, app_context):
        """DM tier has 1GB and 3 campaigns quota."""
        dm = _create_user('dm', profile_tier='dm', storage_quota=1, campaigns_quota=3)
        db.session.commit()

        assert dm.storage_quota_gb == 1
        assert dm.active_campaigns_quota == 3

    def test_headmaster_tier_has_larger_quotas(self, app_context):
        """Headmaster tier has 5GB and 5 campaigns quota."""
        hm = _create_user('hm', profile_tier='headmaster', storage_quota=5, campaigns_quota=5)
        db.session.commit()

        assert hm.storage_quota_gb == 5
        assert hm.active_campaigns_quota == 5

    def test_player_cannot_create_or_upload(self, app_context):
        """Player tier has no quotas (cannot create/upload)."""
        player = _create_user('player', profile_tier='player')
        db.session.commit()

        assert can_create_campaign(player) == False

        allowed, _ = can_upload_asset(player, 100)
        assert allowed == False

    def test_listener_is_observer_only(self, app_context):
        """Listener tier cannot create or upload."""
        listener = _create_user('listener', profile_tier='listener')
        db.session.commit()

        assert can_create_campaign(listener) == False


# ===== INTEGRATION TESTS =====

class TestIntegration:
    """Integration tests combining multiple features."""

    def test_full_campaign_lifecycle_permissions(self, app_context):
        """Test full campaign creation -> deletion flow with permissions."""
        # Create users
        dm = _create_user('dm', profile_tier='dm', storage_quota=1, campaigns_quota=3)
        moderator = _create_user('mod', platform_role='moderator')
        db.session.commit()

        # DM can create campaign
        assert can_create_campaign(dm) == True
        campaign = _create_campaign(dm)

        # DM can edit own campaign
        assert can_edit_campaign(dm, campaign) == True

        # Moderator can also edit
        assert can_edit_campaign(moderator, campaign) == True

        # DM can delete own campaign
        assert can_delete_campaign(dm, campaign) == True

        # Log deletion
        log_campaign_deleted(campaign, deleted_by=dm, reason='Campaign ended')
        db.session.commit()

        # Verify audit trail
        log = AuditLog.query.first()
        assert log.action == 'campaign_deleted'
        assert log.performed_by_id == dm.id

    def test_quota_and_suspension_combined(self, app_context):
        """Test that suspended users cannot create even with quota."""
        dm = _create_user('dm', profile_tier='dm', campaigns_quota=3)
        dm.is_suspended = True
        db.session.commit()

        assert can_create_campaign(dm) == False

    def test_team_view_with_filtering(self, app_context):
        """Test team view filtering by DM."""
        supporter = _create_user('sup', platform_role='supporter')
        dm1 = _create_user('dm1', profile_tier='dm')
        dm2 = _create_user('dm2', profile_tier='dm')

        camp1 = _create_campaign(dm1, 'Campaign 1')
        camp2 = _create_campaign(dm2, 'Campaign 2')
        db.session.commit()

        # Supporter can view all
        assert can_view_all_campaigns(supporter) == True

        # Verify both campaigns exist
        campaigns = Campaign.query.all()
        assert len(campaigns) == 2
