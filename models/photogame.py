import sqlalchemy
from sqlalchemy import Column, Integer, String, DateTime, text, ForeignKey, exc
from sqlalchemy.orm import relationship
import dbsetup
from datetime import datetime


class Client(dbsetup.Base):

    __tablename__ = 'client'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False)  # descriptive name of client
    active = Column(Integer, nullable=False, default=1)  # if =0, then ignore the photo as if it didn't exist

    created_date = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), nullable=False)
    last_updated = Column(DateTime, nullable=True, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP') )

    def __init__(self, **kwargs):
        self.name = kwargs.get('name', None)
        self.active = kwargs.get('active', 1)

    @staticmethod
    def find_client(session, client_id: int) -> object:
        try:
            q = session.query(Client).get(client_id).filter(Client.active == 1)
            c = q.one_or_none()
            return c
        except Exception as e:
            raise


class Campaign(dbsetup.Base):
    __tablename__ = 'campaign'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("client.id", name="fk_campaign_client_id"), nullable=False, index=True)
    name = Column(String(500), nullable=False)  # descriptive name of campaign
    active = Column(Integer, nullable=False, default=1)  # if =0, then ignore the photo as if it didn't exist
    start_date = Column(DateTime, nullable=False) # when campaign starts
    end_date = Column(DateTime, nullable=False) # when campaign ends

    sqlalchemy.UniqueConstraint('name', 'client_id', name='uix_campaign_name_client_id')

    created_date = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), nullable=False)
    last_updated = Column(DateTime, nullable=True, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    def __init__(self, **kwargs):
        self.client_id = kwargs.get('client_id', None)
        self.name = kwargs.get('name', None)
        self.active = kwargs.get('active', 1)
        self.start_date = kwargs.get('start_date', None)
        self.end_date = kwargs.get('end_date', None)

    @staticmethod
    def find_campaign(session, campaign_id: int) -> object:
        try:
            dt_now = datetime.now()
            q = session.query(Campaign).\
                filter(Campaign.id == campaign_id).\
                filter(Campaign.active == 1).\
                filter(Campaign.start_date <= dt_now).\
                filter(Campaign.end_date >= dt_now)
            c = q.one_or_none()
            return c
        except Exception as e:
            raise


# PhotoGame
# This is the photo "library"
class PhotoGameAsset(dbsetup.Base):

    __tablename__ = 'pgasset'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaign.id", name="fk_pgassets_campaign_id"), nullable=False, index=True)
    filepath = Column(String(500), nullable=False)         # e.g. '/mnt/images/49269d/394f9/d431'
    filename = Column(String(100), nullable=False)         # e.g. '970797dfd9f149269d394f9d43179d64.jpeg'
    active = Column(Integer, nullable=False, default=1)  # if =0, then ignore the photo as if it didn't exist
    sqlalchemy.UniqueConstraint('filename', 'campaign_id', name='uix_pgasset_filename_campaign_id')

    created_date = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), nullable=False)
    last_updated = Column(DateTime, nullable=True, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP') )


class GameUser(dbsetup.Base):
    __tablename__ = 'gameuser'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("client.id", name="fk_gameuser_client_id"), nullable=True, index=True)
    client_userid = Column(String(128), nullable=True)
    ii_userid = Column(String(48), nullable=False)

    created_date = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), nullable=False)
    last_updated = Column(DateTime, nullable=True, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP') )


class PhotoGameBallot(dbsetup.Base):

    __tablename__ = "pgballot"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("pgasset.id", name="fk_pgballot_asset_id"), nullable=False, index=True)
    group_id = Column(Integer, nullable=False, index=True)

    created_date = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), nullable=False)
    last_updated = Column(DateTime, nullable=True, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))


class PhotoGameResult(dbsetup.Base):

    __tablename__ = 'pgresult'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaign.id", name="fk_photogameresult_campaign_id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("pgasset.id", name="fk_photogameresult_asset_id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("gameuser.id", name="fk_photogameresult_user_id"), nullable=True, index=True)

    created_date = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), nullable=False)
    last_updated = Column(DateTime, nullable=True, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

# ======================================================================================================
