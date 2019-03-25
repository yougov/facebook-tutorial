__requires__ = ['flask_bootstrap', 'flask', 'requests_toolbelt']

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
FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET')
FACEBOOK_GRAPH_VERSION = os.environ.get('FACEBOOK_GRAPH_VERSION', 'v3.2')
FACEBOOK_SCOPE = 'user_posts'

facebook = sessions.BaseUrlSession(
    f'https://graph.facebook.com/{FACEBOOK_GRAPH_VERSION}/')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


@app.route("/")
def serve_home():
    """
    Serves up the home page

    :return: Renders the home page template
    """

    return flask.render_template("index.html", **globals())


@app.route("/posts")
def posts():
    """
    Retrieve the posts for the user
    """
    token = flask.request.args['access_token']

    resp = facebook.get(
        f'me/feed',
        headers={'Authorization': f'Bearer {token}'},
    )
    if not resp.ok:
        return f'Unexpected resp from Facebook: {resp}'
    return flask.jsonify(resp.json()['data'])


if __name__ == '__main__':
    app.run(host='::', port=int(os.environ.get('PORT', 8080)), debug=True)
