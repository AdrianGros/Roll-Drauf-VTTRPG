"""
Models package - import all models here for easier access.
"""

from vtt.models.role import Role
from vtt.models.user import User
from vtt.models.session import Session
from vtt.models.mfa_backup_code import MFABackupCode
from vtt.models.audit_log import AuditLog
from vtt.models.asset import Asset
from vtt.models.campaign import Campaign
from vtt.models.campaign_map import CampaignMap
from vtt.models.campaign_member import CampaignMember
from vtt.models.game_session import GameSession
from vtt.models.session_state import SessionState
from vtt.models.token_state import TokenState
from vtt.models.invite_token import InviteToken
from vtt.models.character import Character
from vtt.models.spell import Spell
from vtt.models.equipment import Equipment
from vtt.models.inventory_item import InventoryItem
from vtt.models.combat_encounter import CombatEncounter
from vtt.models.combat_event import CombatEvent
from vtt.models.chat_message import ChatMessage
from vtt.models.moderation_report import ModerationReport
from vtt.models.moderation_action import ModerationAction
from vtt.models.scene_stack import SceneStack
from vtt.models.scene_layer import SceneLayer
from vtt.models.session_snapshot import SessionSnapshot
from vtt.models.registration_key import RegistrationKey
from vtt.models.app_theme_settings import AppThemeSettings
from vtt.models.session_map_layer import SessionMapLayer  # M42
from vtt.models.session_token import SessionToken  # M43
from vtt.models.session_initiative import SessionInitiative  # M43
from vtt.models.session_character_assignment import SessionCharacterAssignment
from vtt.models.discord_identity_link import DiscordIdentityLink
from vtt.models.guild import Guild, GuildMembership

__all__ = [
    'Role', 'User', 'Session', 'MFABackupCode', 'AuditLog', 'Asset',
    'Campaign', 'CampaignMap', 'CampaignMember', 'GameSession', 'SessionState', 'TokenState', 'InviteToken',
    'Character', 'Spell', 'Equipment', 'InventoryItem',
    'CombatEncounter', 'CombatEvent',
    'ChatMessage', 'ModerationReport', 'ModerationAction',
    'SceneStack', 'SceneLayer', 'SessionSnapshot',
    'RegistrationKey', 'AppThemeSettings',
    'SessionMapLayer', 'SessionToken', 'SessionInitiative', 'SessionCharacterAssignment', 'DiscordIdentityLink',
    'Guild', 'GuildMembership'
]
