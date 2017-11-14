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

    def tally_results(self, session, votes):
        grp_guid = str(uuid.uuid1()).upper().translate({ord(c): None for c in '-'})
        for vote in votes:
            pgr = photogame.PhotoGameResult(group_guid=grp_guid, asset_id=vote['asset_id'], rank=vote['rank'])
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

    def get_photogame_assets(self, session, campaign_id: int) -> list:

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
