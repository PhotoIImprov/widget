import os
import unittest
import requests
from werkzeug.datastructures import Headers, FileMultiDict
import widget_main
import dbsetup
from models import photogame
import uuid
from datetime import datetime, timedelta
from sqlalchemy import text
import json


class TestPhotoGameAPI(unittest.TestCase):

    test_files = ['TEST4.JPG', 'TEST5.JPG']

    _cleanup_sql = None
    session = None

    def cleanup_sql_command(self) -> str:
        if self._cleanup_sql is None:
            cstr = dbsetup.connection_string(None)
            dbname = cstr.rpartition('/')[-1]
            assert(dbname is not None)
            self._cleanup_sql = "CALL {0}.sp_clean_widget_db()".format(dbname)

        return self._cleanup_sql

    def has_cookie(self, headers) -> bool:
        for header in headers:
            if header[0] == 'Set-Cookie':
                return True
        return False

    def setUp(self):
        self.app = widget_main.app.test_client()

        sql = text(self.cleanup_sql_command())
        self.session = dbsetup.Session()
        result = self.session.execute(sql)
#        result = dbsetup.engine.execute(sql)
        assert(result is not None)
        result.close()
        self.session.commit()

    def create_client(self, session) -> int:
        # create our client
        random_name = str(uuid.uuid1())
        c = photogame.Client(name=random_name, active=1, startdate=datetime.now())
        session.add(c)
        session.commit()
        return c.id

    def create_campaign(self, session, client_id: int) -> int:
        random_name = str(uuid.uuid1())
        start_date = datetime.now() + timedelta(hours=-1)
        end_date = start_date + timedelta(hours=24)
        c = photogame.Campaign(name=random_name, client_id=client_id, active=1, start_date=start_date, end_date=end_date)
        session.add(c)
        session.commit()
        return c.id

    def create_campaign_assets(self, session, campaign_id: int) -> None:
        # read our test file
        for fn in self.test_files:
            pga = photogame.PhotoGameAsset()
            ft = open(os.path.normpath('./photos/' + fn), 'rb')
            img = ft.read()
            ft.close()
            pga.create_asset(campaign_id, img)
            session.add(pga)
        session.commit()

    def create_client_and_campaign(self, session) -> tuple:
        client_id = self.create_client(session)
        campaign_id = self.create_campaign(session, client_id)
        self.create_campaign_assets(session, campaign_id)
        return client_id, campaign_id

    def test_get_images(self):
        # create a client/campaign/assets and verify we can
        # get a ballot
        self.setUp()
        client_id, campaign_id = self.create_client_and_campaign(self.session)
        assert(client_id is not None)
        assert(campaign_id is not None)

        # request a "ballot" for our current game
        rsp = self.app.get(path='/photogame/{0}'.format(campaign_id))
        assert(rsp.status_code == 200)
        assert self.has_cookie(rsp.headers)
        data = json.loads(rsp.data.decode("utf-8"))
        assert(len(data) == 2)

        for asset_id in data:
            rsp = self.app.get(path='/asset/{0}'.format(asset_id))
            assert(rsp.status_code == 200)
            assert not self.has_cookie(rsp.headers)

    def test_get_images_no_campaign(self):
        self.setUp()

    def test_cast_no_ballot(self):
        # cast an empty ballot
        self.setUp()
        rsp = self.app.post(path='/vote', data=None)
        assert(rsp.status_code == 400)
        assert not self.has_cookie(rsp.headers)

    def test_cast_empty_ballot(self):
        # cast an empty ballot
        self.setUp()
        votes = []
        rsp = self.app.post(path='/vote', data=json.dumps(votes))
        assert(rsp.status_code == 400)
        assert not self.has_cookie(rsp.headers)

    def test_cast_fake_ballot(self):
        # cast an fake ballot of bogus asset ids
        self.setUp()
        votes = {'votes': [{'asset_id':0, 'rank':1},{'asset_id':0, 'rank':2}]}
        headers = Headers()
        headers.add('content-type', 'application/json')
        rsp = self.app.post(path='/vote', data=json.dumps(votes), headers=headers)
        assert(rsp.status_code == 400)
        assert not self.has_cookie(rsp.headers)

    def test_cast_real_ballot(self):
        # create a client/campaign/assets and verify we can
        # get a ballot
        self.setUp()
        client_id, campaign_id = self.create_client_and_campaign(self.session)
        assert(client_id is not None)
        assert(campaign_id is not None)

        # request a "ballot" for our current game
        rsp = self.app.get(path='/photogame/{0}'.format(campaign_id))
        if rsp.status_code != 200:
            assert(False)
        assert(rsp.status_code == 200)
        data = json.loads(rsp.data.decode("utf-8"))
        assert(len(data) == 2)
        assert self.has_cookie(rsp.headers)

        user_id = str(uuid.uuid1())
        # create our response
        votes = {'user_id': user_id, 'votes': [{'asset_id':data[0], 'rank':1},{'asset_id':data[1], 'rank':2}]}
        headers = Headers()
        headers.add('content-type', 'application/json')
        rsp = self.app.post(path='/vote', data=json.dumps(votes), headers=headers)
        assert(rsp.status_code == 200)
        assert self.has_cookie(rsp.headers)

        # check that votes are in the DB
        q = self.session.query(photogame.PhotoGameResult)
        pgr_list = q.all()
        assert(pgr_list is not None)
        assert(len(pgr_list) == 2)
        for pgr in pgr_list:
            assert(pgr.asset_id == data[0] or pgr.asset_id == data[1])
            assert(pgr.user_id is not None)

    def initialize_ii_assets(self):
        # This will initialize the assets for the default
        # Image Improv client/campaign
        self.setUp()
        campaign_id = 1
        self.create_campaign_assets(self.session, campaign_id)
