from flask import Flask, jsonify
from flask import request, redirect, make_response, current_app
from flask_jwt import JWT, jwt_required, current_identity
import jwt
from flask_api import status
from flask import send_from_directory
from flask_swagger import swagger
from sqlalchemy import text
from sqlalchemy.orm import Session
from flask_cors import CORS, cross_origin
from logsetup import logger, client_logger, timeit
import os
import datetime
import dbsetup
import initschema
from controllers import photomgr

app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = 'iiwebwidget3177e39'

__version__ = '0.0.1' #our version string PEP 440


def fix_jwt_decode_handler(token):
    secret = current_app.config['JWT_SECRET_KEY']
    algorithm = current_app.config['JWT_ALGORITHM']
    leeway = current_app.config['JWT_LEEWAY']

    verify_claims = current_app.config['JWT_VERIFY_CLAIMS']
    required_claims = current_app.config['JWT_REQUIRED_CLAIMS']

    options = {
        'verify_' + claim: claim in verify_claims
        for claim in ['signature', 'exp', 'nbf', 'iat']
    }

    options.update({
        'require_' + claim: claim in required_claims
        for claim in ['exp', 'nbf', 'iat']
    })

    return jwt.decode(token, secret, options=options, algorithms=[algorithm], leeway=leeway)


# specify the JWT package's call backs for authentication of username/password
# and subsequent identity from the payload in the token
app.config['JWT_EXPIRATION_DELTA'] = datetime.timedelta(days=10)
app.config['JWT_LEEWAY'] = 20
app.config['JWT_VERIFY_CLAIMS'] = ['signature', 'exp'] # keep getting iat "in the future" failure


#
# JWT Callbacks
#
# This is where all authentication calls come, we need to validate the user
def authenticate(username, password):
    return None


# subsequent calls with JWT payload call here to confirm identity
def identity(payload):
    # called with decrypted payload to establish identity
    # based on a user id
    return None


def auth_response_handler(access_token, identity):
    return jsonify({'access_token': access_token.decode('utf-8')})


# set the call-backs to these local functions
_jwt = JWT(app, authenticate, identity)
_jwt.jwt_decode_handler(fix_jwt_decode_handler)
_jwt.auth_response_callback = auth_response_handler # so we can add to the response going back


@app.route("/spec/widget.json")
@timeit()
def spec():
    """
    Specification
    A JSON formatted OpenAPI/Swagger document formatting the API
    ---
    tags:
      - admin
    operationId: widget-specification
    consumes:
      - text/html
    produces:
      - text/html
    responses:
      200:
        description: "look at our beautiful specification"
      500:
        description: "serious error dude"
    """
    swag = swagger(app)
    swag['info']['title'] = "ImageImprov Web Widget API"
    swag['info']['version'] = __version__
    swag['info']['description'] = "Image Improv Web Widget API"\
                                 "## Limits\n"\
                                 "Currently there are no limits on specific users calling these interfaces.\n"

    swag['info']['contact'] = {'name':'apimaster@imageimprov.com'}
    swag['schemes'] = ['https']
    swag['host'] = "api.imageimprov.com"

    swag['paths']["/auth"] = {'post':{'consumes': ['application/json'],
                                      'description':'JWT authentication',
                                      'operationId': 'jwt-auth',
                                      'produces' : ['application/json'],
                                      'parameters': [{'in': 'body',
                                                      'name': 'credentials',
                                                     'schema':
                                                        {'required': ['username', 'password'],
                                                         'properties':{'username':{'type':'string', 'example':'user@gmail.com'},
                                                                        'password':{'type':'string', 'example':'mysecretpassword'}},
                                                         }}],
                                      'responses': {'200':{'description': 'user authenticated',
                                                           'schema':
                                                               {'properties':
                                                                    {'access_token':
                                                                         {'type':'string', 'description': 'JWT access token', 'example' : 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ0b3B0YWwuY29tIiwiZXhwIjoxNDI2NDIwODAwLCJodHRwOi8vdG9wdGFsLmNvbS9qd3RfY2xhaW1zL2lzX2FkbWluIjp0cnVlLCJjb21wYW55IjoiVG9wdGFsIiwiYXdlc29tZSI6dHJ1ZX0.yRQYnWzskCZUxPwaQupWkiUzKELZ49eM7oWxAQK_ZXw'},
                                                                     'email':
                                                                         {'type':'string', 'example': 'user@gmail.com'}
                                                                     }
                                                                }
                                                           },
                                                    '401':{'description': 'user authentication failed'}
                                                    },
                                      'summary' : "JWT authentication",
                                      'tags':['user']}
                              }

    swag['securityDefinitions'] = {'api_key': {'type': 'apiKey', 'name': 'key', 'in': 'query'}}
    swag['securityDefinitions'] = {'JWT': {'type': 'apiKey', 'name': 'access_token', 'in': 'header'}}
    swag['swagger'] = "2.0"

    resp = make_response(jsonify(swag), status.HTTP_200_OK)
    resp.headers['Content-Type'] = "application/json"
    resp.headers['Access-Control-Allow-Origin'] = "*"
    resp.headers['Access-Control-Allow-Headers'] = "Content-Type"
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST'
    resp.headers['Server'] = 'Flask'
    return resp


@app.route("/photogame/<int:campaign_id>", methods=['GET'])
@cross_origin(origins='*')
# @jwt_required()
@timeit()
def get_images(campaign_id: int):
    """
    Fetch Image ballot
    Returns a list of images that can then be voted on.
    ---
    tags:
      - game
    operationId: get-images
    consumes:
      - text/plain
    parameters:
      - in: path
        name: campaign_id
        description: "specifies campaign for client"
        required: true
        type: integer
    security:
      - JWT: []
    produces:
      - image/jpeg
    responses:
      200:
        description: "success"
      400:
        description: "missing required arguments"
      500:
        description: "error retrieving images, something serious"
    """
    pm = photomgr.PhotoGameMgr()
    session = dbsetup.Session()
    try:
        bl = pm.get_photogame_assets(session, campaign_id)
        if len(bl) == 0:
            return make_response("no images for campaign {0}".format(campaign_id), status.HTTP_204_NO_CONTENT)

        session.commit()
    except Exception as e:
        session.rollback()
    finally:
        session.close()

    return make_response("not implemented", status.HTTP_501_NOT_IMPLEMENTED)


if __name__ == '__main__':
    dbsetup.metadata.create_all(bind=dbsetup.engine, checkfirst=True)
    if not dbsetup.is_gunicorn():
        if "DEBUG" in os.environ:
            if os.environ.get('DEBUG', '0') == '1':
                dbsetup._DEBUG = 1

        app.run(host='0.0.0.0', port=8081)
