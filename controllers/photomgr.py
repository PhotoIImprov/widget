from models import photogame
from random import randint, shuffle
import os
import uuid

class PhotoImageAsset():
    _binary_image = None
    _extension = None
    _asset_id = None

    def __init__(self, **kwargs):
        if len(kwargs) == 0:
            return
        pga = kwargs.get('pga', None)
        if pga is not None:
            self._asset_id = pga.id
            self._extension = pga.filename[-3:]
            load_image = kwargs.get('load_image', False)
            if load_image:
                try:
                    ft = open(os.path.normpath(pga.filepath + '/' + pga.filename), 'rb')
                    self._binary_image = ft.read()
                except Exception as e:
                    raise
                finally:
                    ft.close()

class PhotoGameMgr():

    def __init__(self, **kwargs):
        if len(kwargs) == 0:
            return

    def find_ii_user(self, session, user_id: str) -> int:
        try:
            q = session.query(photogame.GameUser).filter(photogame.GameUser.ii_userid == user_id)
            gu = q.one_or_none()
            if gu is not None:
                return gu.id

        except Exception as e:
            raise

    def find_client_and_campaign_from_asset(self, session, asset_id: int) -> (int, int):
        try:
            q = session.query(photogame.Campaign).\
                join(photogame.PhotoGameAsset, photogame.PhotoGameAsset.campaign_id == photogame.Campaign.id).\
                filter(photogame.PhotoGameAsset.id == asset_id)
            c = q.one_or_none()
            return c.client_id, c.id
        except Exception as e:
            raise

    def find_client_user(self, session, user_id: str, ii_user_id: str, asset_id: int) -> int:
        try:
            q = session.query(photogame.GameUser).filter(photogame.GameUser.client_userid == user_id)
            gu = q.one_or_none()
            if gu is not None:
                return gu.id

            # if we have a client user_id and it's not in our DB, we need
            # to create a record for it
            client_id, campaign_id = self.find_client_and_campaign_from_asset(session, asset_id)

            # now we can create a user
            gu = photogame.GameUser(client_id=client_id, client_user_id=user_id, ii_user_id=ii_user_id)
            session.add(gu)
            session.commit()
            return gu.id

        except Exception as e:
            raise

    def tally_results(self, session, client_user_id: str, ii_user_id: str, votes: list):
        grp_guid = str(uuid.uuid1()).upper().translate({ord(c): None for c in '-'})

        # lookup the user_id provided and get the FK
        gu_id = None
        asset_id = votes[0]['asset_id']
        if client_user_id is not None:
            gu_id = self.find_client_user(session, client_user_id, ii_user_id, asset_id)
        else:
            gu_id = self.find_ii_user(session, ii_user_id)

        for vote in votes:
            pgr = photogame.PhotoGameResult(group_guid=grp_guid, asset_id=vote['asset_id'], rank=vote['rank'], user_id=gu_id)
            session.add(pgr)
        session.commit()
        return

    def campaign_ballot(self, session, campaign_id: int, ballot_size: int) -> list:

        try:
            q = session.query(photogame.PhotoGameAsset).\
                filter(photogame.PhotoGameAsset.campaign_id == campaign_id).\
                filter(photogame.PhotoGameAsset.active == 1)
            asset_list = q.all()

            # from the asset list we need to create a random ballot
            assert(len(asset_list) >= ballot_size)
            shuffle(asset_list)
            return asset_list[:ballot_size]
        except Exception as e:
            raise e

    def read_asset(self, session, asset_id: int) -> bytes:
        # get the filename information from the PhotoGameAsset record
        try:
            asset = session.query(photogame.PhotoGameAsset).get(asset_id)
            if asset is None:
                return None
            ft = open(os.path.normpath(asset.filepath + '/' + asset.filename), 'rb')
            image = ft.read()
            ft.close()
            return image
        except Exception as e:
            raise

    def get_photogame_assets(self, session, campaign_id: int, ii_user_id: str) -> list:

        pl = []
        o_campaign = photogame.Campaign.find_campaign(session, campaign_id)
        if o_campaign is None:
            return pl  # no active campaign

        # okay, this client & campaign are active, let's get
        # the photo assets for the game
        bl = self.campaign_ballot(session, campaign_id, ballot_size=2)
        if len(bl) == 0:
            return pl

        # we have a group of photos (ballot_size=2), but these are just
        # asset ids, we need to get the images and return them
        for pga in bl:
            pi = PhotoImageAsset(pga=pga, load_image=False)
            pl.append(pi)

        return pl

    def user_id_from_cookie(self, session, cookies: dict) -> str:
        # read the ii_user_id from the cookie (if present)
        ii_user_id = cookies.get('user_id', None)
        if ii_user_id is None:
            ii_user_id = str(uuid.uuid1())

        return ii_user_id