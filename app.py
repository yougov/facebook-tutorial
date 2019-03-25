__requires__ = ['flask_bootstrap', 'flask', 'requests_toolbelt']

import urllib.parse
import logging
import os

from flask_bootstrap import Bootstrap
import flask
from requests_toolbelt import sessions

app = flask.Flask(__name__)
app.config.from_object(__name__)
app.secret_key = "Secret key"
Bootstrap(app)

FACEBOOK_APP_ID = os.environ['FACEBOOK_APP_ID']
FACEBOOK_APP_SECRET = os.environ['FACEBOOK_APP_SECRET']

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
        return resp.json()["access_token"]
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
    user_authorized = "user_token" in TOKENS

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
    try:
        TOKENS["user_token"] = get_user_token(flask.request.args.get("code"))

        return flask.redirect("/")
    except NotAuthorizedException:
        return 'Access was not granted or authorization failed', 403


def callback_url():
    return urllib.parse.urljoin(flask.request.base_url, '/callback')


@app.route("/posts")
def posts():
    # Make sure there is a token
    try:
        token = TOKENS["user_token"]
    except KeyError:
        return 'Not authorized', 401

    resp = facebook.get(
        f'me/feed',
        headers={'Authorization': f'Bearer {token}'},
    )
    if not resp.ok:
        return f'Unexpected resp from Facebook: {resp}'
    return resp.text


if __name__ == '__main__':
    # Register an app token at start-up (purely as
    # validation that configuration for Facebook is correct)
    TOKENS["app_token"] = get_app_token()
    app.run(host='::', port=int(os.environ.get('PORT', 8080)), debug=True)
