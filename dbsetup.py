from sqlalchemy        import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm    import sessionmaker
from enum import Enum
import os
from flask import request
from sqlalchemy import exc
from sqlalchemy import event
from sqlalchemy import select
import warnings


class ImageType(Enum):
    UNKNOWN = 0
    JPEG = 1
    PNG = 2
    BITMAP = 3
    TIFF = 4


class EnvironmentType(Enum):
    NOTSET = -1
    UNKNOWN = 0
    DEV = 1
    QA = 2
    STAGE = 3
    PROD = 4


class Configuration():
    UPLOAD_CATEGORY_PICS = 4


def determine_environment(hostname):
    if hostname is None:
        try:
            hostname = str.upper(os.uname()[1])
        except Exception as e:
            hostname = str.upper(os.environ['COMPUTERNAME'])

    if "DEV" in hostname:
        return EnvironmentType.DEV
    elif "ULTRAMAN" in hostname:
        return EnvironmentType.DEV
    elif "PROD" in hostname:
        return EnvironmentType.PROD
    elif "INSTANCE" in hostname:
        return EnvironmentType.PROD
    elif "STAGE" in hostname:
        return EnvironmentType.STAGE
    elif "QA" in hostname:
        return EnvironmentType.QA

    return EnvironmentType.UNKNOWN


def connection_string(environment):

    if environment is None:
        environment = determine_environment(None)
    if environment == EnvironmentType.DEV:
        if os.name == 'nt': # ultraman
            return 'mysql+pymysql://python:python@localhost:3306/widget'
        else:
            return 'mysql+pymysql://python:python@192.168.1.16:3306/widget'

    if environment == EnvironmentType.PROD:
        return 'mysql+pymysql://python:python@127.0.0.1:3306/widget'

    return None


def get_fontname(environment):
    if environment == EnvironmentType.DEV:
        if os.name == 'nt': # ultraman
            return 'c:/Windows/Boot/Fonts/segmono_boot.ttf'
        else:
            return '/usr/share/fonts/truetype/ubuntu-font-family/UbuntuMono-B.ttf'
    if environment == EnvironmentType.PROD:
        return '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'

    return None


def resource_files(environment):
    if environment == EnvironmentType.DEV:
        if os.name == 'nt': # ultraman
            return 'c:/dev/widget/tests/photos'
        else:
            return '/home/hcollins/dev/widget/tests/photos'
    if environment == EnvironmentType.PROD:
        return '/home/bp100a/widget/tests/photos'

    return None


def image_store(environment: EnvironmentType) -> str:
    if environment == EnvironmentType.DEV:
        if os.name == 'nt': # ultraman
            return 'c:/dev/image_files'
        else:
            return '/mnt/image_files'

    if environment == EnvironmentType.PROD:
        return '/mnt/gcs-photos'

    return None


def template_dir(environment: EnvironmentType) -> str:

    if environment is None:
        environment = determine_environment(None)

    if environment == EnvironmentType.DEV:
        if os.name == 'nt': # ultraman
            return 'c:/dev/widget/templates'
        else:
            return '/home/hcollins/dev/widget/templates'

    if environment == EnvironmentType.PROD:
        return '/home/bp100a/widget/templates'

    return None


def root_url(environment: EnvironmentType) -> str:
    if environment is None:
        environment = determine_environment(None)

    if environment == EnvironmentType.DEV:
        return 'http://localhost:8080'

    if environment == EnvironmentType.PROD:
        return 'https://api.imageimprov.com'


def is_gunicorn():
    _is_gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")
    return _is_gunicorn

engine = create_engine(connection_string(None), echo=False, pool_recycle=3600)
Session = sessionmaker(bind=engine)
Base = declarative_base()
metadata = Base.metadata
metadata.create_all(bind=engine, checkfirst=True)
_DEBUG = False


@event.listens_for(engine, "engine_connect")
def ping_connection(connection, branch):
    if branch:
        # "branch" refers to a sub-connection of a connection,
        # we don't want to bother pinging on these.
        return

    # turn off "close with result".  This flag is only used with
    # "connectionless" execution, otherwise will be False in any case
    save_should_close_with_result = connection.should_close_with_result
    connection.should_close_with_result = False

    try:
        # run a SELECT 1.   use a core select() so that
        # the SELECT of a scalar value without a table is
        # appropriately formatted for the backend
        connection.scalar(select([1]))
    except exc.DBAPIError as err:
        # catch SQLAlchemy's DBAPIError, which is a wrapper
        # for the DBAPI's exception.  It includes a .connection_invalidated
        # attribute which specifies if this connection is a "disconnect"
        # condition, which is based on inspection of the original exception
        # by the dialect in use.
        if err.connection_invalidated:
            # run the same SELECT again - the connection will re-validate
            # itself and establish a new connection.  The disconnect detection
            # here also causes the whole connection pool to be invalidated
            # so that all stale connections are discarded.
            connection.scalar(select([1]))
        else:
            raise
    finally:
        # restore "close with result"
        connection.should_close_with_result = save_should_close_with_result


# just for fun
QUOTES = (
    ('He was a wise man who invented beer.', 'Plato'),
    ('Beer is made by men, wine by God.', 'Martin Luther'),
    ('Who cares how time advances? I am drinking ale today.', 'Edgar Allen Poe'),
    ('It takes beer to make thirst worthwhile.', 'German proverb'),
    ('Beer: So much more than just a breakfast drink.', 'Homer Simpson'),
    ('History flows forward on a river of beer.', 'Anonymous'),
    ('Work is the curse of the drinking classes.', 'Oscar Wilde'),
    ('For a quart of ale is a dish for a king.', 'William Shakespeare, "A Winter\'s Tale"'),
    ('Beer. Now there\'s a temporary solution.', 'Homer Simpson'),
    ('What care I how time advances? I am drinking ale today', 'Edgar Allen Poe'),
    ('Beer, if drunk in moderation, softens the temper, cheers the spirit and promotes health', 'Thomas Jefferson'),
    ('In a study, scientists report that drinking beer can be good for the liver. I\'m sorry, did I say scientists? I mean Irish people', 'Tina Fey'),
    ('Most people hate the taste of beer - to begin with. It is, however, a prejudice.', 'Winston Churchill'),
    ('For a quart of Ale is a dish for a king', 'William Shakespeare'),
    ('I am a firm believer in the people. If given the truth, they can be depended upon to meet any national crisis. The great point is to bring them the real facts, and beer', 'Abraham Lincoln'),
    ('Whoever drinks beer, he is quick to sleep; whoever sleeps long, does not sin; whoever does not sin, enters Heaven! Thus, let us drink beer!', 'Martin Luther'),
    ('Milk is for babies. When you grow up you have to drink beer', 'Arnold Schwarzenegger'),
    ('I look like the kind of guy that has a bottle of beer in my hand', 'Charles Bronson'),
    ('Yes, sir. I\'m a real Souther boy. I got a red neck, white socks, and a BlueRibbon beer.', 'Billy Carter'),
    ('Give a man a beer, waste an hour. Teach a man to brew, and waste a lifetime!', 'Bill Owen'),
    ('He was a wise man who invented beer.', 'Plato'),
    ('Beer\'s intellectual. What a shame so many idiots drink it.', 'Ray Bradbury'),
    ('Beer is proof that God loves us and wants us to be happy', 'Benjamin Franklin'),
    ('You can\'t be a real country unless you have a beer and an airline - it helps if you have some kind of football team, or some nuclear weapons, but in the very least you need a beer', 'Frank Zappa'),
    ('The best beer in the world is the one in my hand', 'Charles Papazian'),
    ('Give my people plenty of beer, good beer, and cheap beer, and you will have no revolution among them', 'Queen Victoria')
)
