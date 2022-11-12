import tekore as tk

from flask import Flask, request, redirect, session
import requests
from requests.auth import HTTPBasicAuth

client_id = ""
client_secret = ""
SPOTIFY_GET_CURRENT_TRACK_URL = 'https://api.spotify.com/v1/me/player/currently-playing'
redirect_url = "http://localhost:5000/callback"
conf = (client_id, client_secret, redirect_url)
cred = tk.Credentials(*conf)
spotify = tk.Spotify()

auths = {}  # Ongoing authorisations: state -> UserAuth
users = {}  # User tokens: state -> token (use state as a user ID)

in_link = '<a href="/login">login</a>'
out_link = '<a href="/logout">logout</a>'
login_msg = f'You can {in_link} or {out_link}'

# https://accounts.spotify.com/en/authorize?client_id=&redirect_uri=http://localhost:5000/callback&response_type=code&scope=user-read-currently-playing&state=rRY1muPXK-Z9Z5MypYMZ4ybMzyaYJQvBR0KKWpZlWsM&show_dialog=true


def app_factory() -> Flask:
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'aliens'

    @app.route('/', methods=['GET'])
    def main():
        user = session.get('user', None)
        token = users.get(user, None)

        # Return early if no login or old session
        if user is None or token is None:
            session.pop('user', None)
            return f'User ID: None<br>{login_msg}'

        page = f'User ID: {user}<br>{login_msg}'
        if token.is_expiring:
            token = cred.refresh(token)
            users[user] = token

        try:
            with spotify.token_as(token):
                playback = spotify.playback_currently_playing()

            item = playback.item if playback else None
            page += f'<br>Now playing: {item.name} by {item.artists[0].name}. Link to track is here: {item.external_urls["spotify"]}'
        except tk.HTTPError:
            page += '<br>Error in retrieving now playing!'

        return page

    @app.route('/login', methods=['GET'])
    def login():
        if 'user' in session:
            return redirect('/', 307)

        scope = tk.scope.user_read_currently_playing
        auth = tk.UserAuth(cred, scope)
        auths[auth.state] = auth
        return redirect(auth.url, 307)

    @app.route('/callback', methods=['GET'])
    def login_callback():
        code = request.args.get('code', None)
        state = request.args.get('state', None)
        auth = auths.pop(state, None)

        if auth is None:
            return 'Invalid state!', 400

        token = auth.request_token(code, state)
        session['user'] = state
        users[state] = token
        return redirect('/', 307)

    @app.route('/logout', methods=['GET'])
    def logout():
        uid = session.pop('user', None)
        if uid is not None:
            users.pop(uid, None)
        return redirect('/', 307)

    return app

if __name__ == '__main__':
    application = app_factory()
    application.run('127.0.0.1', 5000)
