import sqlalchemy
from sqlalchemy import Column, Integer, String, DateTime, text, ForeignKey, exc
from sqlalchemy.orm import relationship
import dbsetup
from datetime import datetime
import uuid
import os, os.path, errno
from retrying import retry
from logsetup import logger, timeit
import string


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

    def create_asset(self, campaign_id: int, img: bytes, extension='JPG'):
        # first create asset name
        self.campaign_id = campaign_id
        asset_uuid = uuid.uuid1()
        self.filename = str(asset_uuid).upper().translate({ord(c): None for c in '-'}) + '.' + extension
        mnt_point = dbsetup.image_store(dbsetup.determine_environment(None)) # get the mount point
        self.filepath = mnt_point + '/' + self.create_sub_path(asset_uuid)

        # now compose the filename
        full_fn = self.filepath + '/' + self.filename

        # finally write the file to longterm storage
        self.safe_write_file(path_and_name=full_fn, img=img)
        return

    def create_sub_path(self, asset_uuid) -> str:
        # paths are generated from filenames
        # paths are designed to hold no more 1000 entries,
        # so must be 10 bits in length. Three levels should give us 1 billion!

        # Note: The clock interval is 1E-7 (100ns). We are generating 2 million pictures
        #       per diem, which works out to 24 pictures/sec, or ~43 seconds to generate
        #       1000 pictures (filling up a directory). So we need to ignore the first
        #       29 bits of our timesequence. Hence the shifting and masking.
        #
        #       So ideally the lowest level directory will contain 1000 images,
        #       and each branch of directories will have 1000 sub-directories
        #       so three levels of this gives us a capacity for 1 billion images
        #       which is probably about 2 years of growth.

        # our filename is a uuid, we need to convert it back to one

        dir1 = ((asset_uuid.time_low >> 29) & 0x7) + ((asset_uuid.time_mid << 3) & 0x3F8)
        dir2 = ((asset_uuid.time_mid >> 3) & 0x3FF)
        dir3 = ((asset_uuid.time_mid >> 13) & 0x3FF)
        return '{:03}/{:03}/{:03}'.format(dir3, dir2, dir1)

    def create_full_filename(self, filepath: str, root_filename: str, extension: str) -> str:
        return filepath + "/" + root_filename + "." + extension

    def mkdir_p(self, path: str) -> None:
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise
        return

    @timeit()
    def write_file(self, path_and_name: str, fdata: bytes) -> None:
        if fdata is None or path_and_name is None:
            raise Exception(errno.EINVAL)

        # okay we have a path and a filename, so let's try to create it
        fp = open(path_and_name, "wb")
        if fp is None:
            raise Exception(errno.EBADFD)

        bytes_written = fp.write(fdata)
        if bytes_written != len(fdata):
            raise Exception(errno.EBADFD)
        fp.close()
        return

    @retry(wait_exponential_multiplier=100, wait_exponential_max=1000, stop_max_attempt_number=10)
    def safe_write_file(self, path_and_name: str, img: bytes) -> None:
        # the path may not be created, so we try to write the file
        # catch the exception and try again
        try:
            self.write_file(os.path.normpath(path_and_name), img)
        except OSError as err:
            # see if this is our "no such dir error", if so we can try again, otherwise leave
            if err.errno != errno.ENOENT:
                raise
            # okay, the directory doesn't exist, so make it
            try:
                path_only = os.path.dirname(os.path.normpath(path_and_name))
                self.mkdir_p(os.path.normpath(path_only))
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise

            # try writing again
            self.write_file(os.path.normpath(path_and_name), img)
        return


class GameUser(dbsetup.Base):
    __tablename__ = 'gameuser'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("client.id", name="fk_gameuser_client_id"), nullable=True, index=True)
    client_userid = Column(String(128), nullable=True)
    ii_userid = Column(String(48), nullable=False)

    created_date = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), nullable=False)
    last_updated = Column(DateTime, nullable=True, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP') )

    def __init__(self, **kwargs):
        self.client_id = kwargs.get('client_id', None)
        self.client_user_id = kwargs.get('client_user_id', None)
        self.ii_userid = kwargs.get('ii_user_id', str(uuid.uuid1()))

class PhotoGameResult(dbsetup.Base):

    __tablename__ = 'pgresult'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("pgasset.id", name="fk_photogameresult_asset_id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("gameuser.id", name="fk_photogameresult_user_id"), nullable=True, index=True)
    group_guid = Column(String(32), nullable=False, index=True)
    rank = Column(Integer, nullable=False)

    created_date = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'), nullable=False)
    last_updated = Column(DateTime, nullable=True, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))


    def __init__(self, **kwargs):
        self.asset_id = kwargs.get('asset_id', None)
        self.group_guid = kwargs.get('group_guid', None)
        self.rank = kwargs.get('rank', None)
        self.user_id = kwargs.get('user_id', None)
# ======================================================================================================
