"""Authorization helpers for community and moderation flows."""

from vtt_app.models import Campaign, CampaignMember, User


def is_admin(user: User) -> bool:
    if not user or not user.role:
        return False
    return str(user.role.name).lower() == "admin"


def is_active_member(campaign: Campaign, user_id: int) -> bool:
    if campaign.owner_id == user_id:
        return True
    member = CampaignMember.query.filter_by(
        campaign_id=campaign.id,
        user_id=user_id,
        status="active",
    ).first()
    return member is not None


def is_dm_or_owner(campaign: Campaign, user_id: int) -> bool:
    if campaign.owner_id == user_id:
        return True
    member = CampaignMember.query.filter_by(
        campaign_id=campaign.id,
        user_id=user_id,
        status="active",
    ).first()
    return bool(member and member.campaign_role == "DM")


def can_moderate_campaign(campaign: Campaign, user: User) -> bool:
    return is_admin(user) or is_dm_or_owner(campaign, user.id)


def can_apply_ban(user: User) -> bool:
    return is_admin(user)
