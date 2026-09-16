from flask import Flask, g, redirect, url_for
from flask_oidc import OpenIDConnect
from box_sdk_gen import BoxClient, BoxCCGAuth, CCGConfig

import config

app = Flask(__name__)
app.config.update({
    'SECRET_KEY': config.flask_secret_key,
    'OIDC_CLIENT_SECRETS': './client_secrets.json',
    'OIDC_SCOPES': 'openid profile'
})

oidc = OpenIDConnect(app)


# Main application route
@app.route('/')
def start():
    return redirect(url_for('.box_auth'))


# Box user verification
@app.route('/box_auth')
@oidc.require_login
def box_auth():
    box = Box()
    return box.validate_user(g.oidc_user.profile)


# Box user class
class Box(object):
    def __init__(self):
        ccg_config = CCGConfig(
            client_id=config.box_client_id,
            client_secret=config.box_client_secret,
            enterprise_id=config.box_enterprise_id,
        )
        self.auth = BoxCCGAuth(config=ccg_config)
        self.box_client = BoxClient(auth=self.auth)

    # Find the Box user bound to this Okta user
    def validate_user(self, okta_user):
        users = self.box_client.users.get_users(
            external_app_user_id=okta_user['sub']
        )

        if not users.entries:
            return self.create_user(okta_user)

        return self.authenticate_as_user(users.entries[0])

    # Create a Box App User bound to this Okta user
    def create_user(self, okta_user):
        space = 1073741824   # ~1 GB

        self.box_client.users.create_user(
            okta_user['name'],
            is_platform_access_only=True,
            space_amount=space,
            external_app_user_id=okta_user['sub']
        )

        return f"New user created: {okta_user['name']}"

    # Act as the discovered Box user
    def authenticate_as_user(self, box_user):
        user_auth = self.auth.with_user_subject(box_user.id)
        user_client = BoxClient(auth=user_auth)

        current_user = user_client.users.get_user_me()
        return f'Hello {current_user.name}'
