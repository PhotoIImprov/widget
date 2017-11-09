import os
import unittest
import requests
from werkzeug.datastructures import Headers, FileMultiDict
import widget_main
import dbsetup
from models import photogame
import uuid
from datetime import datetime, timedelta

class TestPhotoGameAPI(unittest.TestCase):

    def setUp(self):
        self.app = widget_main.app.test_client()

    def create_client(self, session) -> int:
        # create our client
        random_name = str(uuid.uuid1())
        c = photogame.Client(name=random_name, active=1, startdate=datetime.now())
        session.add(c)
        session.commit()
        return c.id

    def create_campaign(self, session, client_id: int) -> int:
        random_name = str(uuid.uuid1())
        start_date = datetime.now()
        end_date = start_date + timedelta(hours=24)
        c = photogame.Campaign(name=random_name, client_id=client_id, active=1, start_date=start_date, end_date=end_date)
        session.add(c)
        session.commit()
        return c.id

    def create_client_and_campaign(self, session) -> tuple:
        client_id = self.create_client(session)
        campaign_id = self.create_campaign(session, client_id)
        return client_id, campaign_id

    def test_get_images_no_client_id(self):
        self.setUp()
        session = dbsetup.Session()
        client_id, campaign_id = self.create_client_and_campaign(session)
        assert(client_id is not None)
        assert(campaign_id is not None)

        # request a "ballot" for our current game
        rsp = self.app.get(path='/photogame/{0}'.format(campaign_id))
        assert(rsp.status_code == 204)
