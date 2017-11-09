from models import photogame


class PhotoGameMgr():

    def __init__(self, **kwargs):
        if len(kwargs) == 0:
            return

    def campaign_ballot(self, session, campaign_id: int) -> list:

        try:
            q = session.query(photogame.PhotoGameBallot).\
                join(photogame.PhotoGameAsset, photogame.PhotoGameAsset.id == photogame.PhotoGameBallot.asset_id).\
                filter(photogame.PhotoGameAsset.campaign_id == campaign_id).\
                filter(photogame.PhotoGameAsset.active == 1)
            bl = q.all()
            return bl
        except Exception as e:
            raise e

    def get_photogame_assets(self, session, campaign_id: int) -> list:

        pl = []
        o_campaign = photogame.Campaign.find_campaign(session, campaign_id)
        if o_campaign is None:
            return pl  # no active campaign

        # okay, this client & campaign are active, let's get
        # the photo assets for the game
        bl = self.campaign_ballot(session, campaign_id)
        # 'bl' is a list of pre-computed ballots for this game
        if len(bl) == 0:
            return pl

        # okay we have to find a "group" of photos we haven't already
        # displayed to the user and send back those images
        return pl