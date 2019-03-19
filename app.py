#!/usr/bin/env python

import urllib.parse
import logging

from flask_bootstrap import Bootstrap
import flask
from requests_toolbelt import sessions

app = flask.Flask(__name__)
app.config.from_object(__name__)
app.secret_key = "Secret key"
Bootstrap(app)

FACEBOOK_APP_ID = "YOUR_APP_ID"
FACEBOOK_APP_SECRET = "YOUR_APP_SECRET"

TOKENS = {}

facebook = sessions.BaseUrlSession('https://graph.facebook.com/v2.4/')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


class NotAuthorizedException(Exception):
    pass


# OAuth functions


def get_app_token():
    """
    Get an app token based on app ID and secret

    :return:
    """
    params = dict(
        client_id=FACEBOOK_APP_ID,
        client_secret=FACEBOOK_APP_SECRET,
        grant_type='client_credentials',
    )
    try:
        resp = facebook.get('/oauth/access_token', params=params)
        resp.raise_for_status()
        return urllib.parse.parse_qs(resp.text)["access_token"]
    except KeyError:
        logging.log(logging.ERROR, resp.text)
        raise NotAuthorizedException(
            "Authorization error", "App access token not found")


def get_user_token(code):
    params = dict(
        client_id=FACEBOOK_APP_ID,
        redirect_uri=callback_url(),
        client_secret=FACEBOOK_APP_SECRET,
        code=code,
    )
    try:
        resp = facebook.get(
            f'oauth/access_token',
            params=params,
        )
        return resp.json()["access_token"]
    except KeyError:
        logging.log(logging.ERROR, resp.text)
        raise NotAuthorizedException(
            "Authorization error", "User access token not found")

# App routes


@app.route("/")
def serve_home():
    """
    Serves up the home page

    :return: Renders the home page template
    """

    # Check whether the user has authorized the app,
    # if authorized login button will not be displayed
    user_authorized = True if "user_token" in TOKENS else False

    return flask.render_template("index.html", authorized=user_authorized)


@app.route("/authorize")
def authorize_facebook():
    """
    Redirects the user to the Facebook login page to authorize the app:
    - response_type=code
    - Scope requests is to post updates on behalf of
      the user and read their stream

    :return: Redirects to the Facebook login page
    """
    qs = urllib.parse.urlencode(dict(
        client_id=FACEBOOK_APP_ID,
        redirect_uri=callback_url(),
        scope='publish_actions',
    ))
    url = 'https://www.facebook.com/dialog/oauth?' + qs
    return flask.redirect(url)


@app.route("/callback")
def handle_callback():
    """
    Handles callback after user authorization of app,
    calling back to exchange code for access token

    :return:
    """
    global TOKENS

    try:
        TOKENS["user_token"] = get_user_token(flask.request.args.get("code"))

        return flask.redirect("/")
    except NotAuthorizedException:
        return 'Access was not granted or authorization failed', 403


def callback_url():
    return urllib.parse.urljoin(flask.request.base_url, '/callback')


@app.route("/helloworld", methods=["POST"])
def hello_world():
    global TOKENS
    lat_lng = None

    # Make sure there is a token
    try:
        token = TOKENS["user_token"]
    except KeyError:
        return 'Not authorized', 401

    # Get a place id to include in the post, search for
    # coffee within 10000 metres and grab first returned
    try:
        args = flask.request.args
        params = dict(
            q='coffee shop',
            type='place',
            center=f'{args.get("lat")},{args.get("lng")}',
            distance=10000,
        )
        resp = facebook.get(
            f'search',
            params=params,
            headers={'Authorization': f'Bearer {token}'},
        )

        if not resp.ok:
            logging.log(logging.ERROR, resp.text)
            return f'Unexpected HTTP return code from Facebook: {resp}'

    except Exception as e:
        logging.log(logging.ERROR, str(e))
        return 'Unknown error calling Graph API', 502

    # Attempt to add place to post (if one is returned)
    try:
        places = resp.json()
        post = {
            "message": "Heading+out+for+coffee.+Hello+World%21",
            "place": places["data"][0]["id"]
        }
        lat_lng = {
            "name": places["data"][0]["name"],
            "lat": places["data"][0]["location"]["latitude"],
            "lng": places["data"][0]["location"]["longitude"]
        }

    except (KeyError, IndexError):
        post = {
            "message": "Staying+home+for+coffee.+Goodbye+World%21"
        }

    try:
        resp = facebook.post(
            'me/feed',
            headers=dict(Authorization=f'Bearer {token}'),
            data=post,
        )

        if not resp.ok:
            logging.log(logging.ERROR, resp.text)
            return f'Unexpected HTTP return code from Facebook: {resp}'
    except Exception as e:
        logging.log(logging.ERROR, str(e))
        return 'Unknown error calling Graph API', 502

    if lat_lng is None:
        return '', 201
    else:
        return flask.jsonify(**lat_lng), 201


if __name__ == '__main__':
    # Register an app token at start-up (purely as
    # validation that configuration for Facebook is correct)
    TOKENS["app_token"] = get_app_token()
    app.run(host="0.0.0.0", port=8080, debug=True)
