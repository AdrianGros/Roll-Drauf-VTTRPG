"""Private Atlas authoring and separately stored immutable reader publications."""
from vtt.extensions import db
from vtt.utils.time import utcnow


class AtlasWorld(db.Model):
    __tablename__='atlas_worlds'
    id=db.Column(db.String(36),primary_key=True)
    owner_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False,index=True)
    graph=db.Column(db.JSON,nullable=False)
    revision=db.Column(db.Integer,nullable=False,default=1)
    graph_bytes=db.Column(db.Integer,nullable=False)
    updated_at=db.Column(db.DateTime,nullable=False,default=utcnow)


class AtlasMember(db.Model):
    __tablename__='atlas_members'
    world_id=db.Column(db.String(36),db.ForeignKey('atlas_worlds.id'),primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('users.id'),primary_key=True)
    role=db.Column(db.String(12),nullable=False)


class AtlasMap(db.Model):
    __tablename__='atlas_maps'
    id=db.Column(db.String(36),primary_key=True)
    world_id=db.Column(db.String(36),db.ForeignKey('atlas_worlds.id'),nullable=False,index=True)
    revision=db.Column(db.Integer,nullable=False,default=1)
    width=db.Column(db.Integer,nullable=False)
    height=db.Column(db.Integer,nullable=False)
    storage_key=db.Column(db.String(250),nullable=False,unique=True)
    storage_provider=db.Column(db.String(20),nullable=False)
    size_bytes=db.Column(db.Integer,nullable=False)
    lease_user_id=db.Column(db.Integer,db.ForeignKey('users.id'))
    lease_tab=db.Column(db.String(36))
    lease_expires=db.Column(db.DateTime)


class AtlasPublication(db.Model):
    __tablename__='atlas_publications'
    id=db.Column(db.String(36),primary_key=True)
    world_id=db.Column(db.String(36),db.ForeignKey('atlas_worlds.id'),nullable=False,unique=True)
    projection=db.Column(db.JSON,nullable=False)
    storage_key=db.Column(db.String(250),nullable=False,unique=True)
    storage_provider=db.Column(db.String(20),nullable=False)
    size_bytes=db.Column(db.Integer,nullable=False)
    created_at=db.Column(db.DateTime,nullable=False,default=utcnow)
