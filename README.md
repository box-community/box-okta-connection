# Connect Okta identities to Box App Users

A minimal, runnable Flask app that signs users in with Okta, finds or
creates a matching Box App User, and makes Box API calls scoped to that
user.

[Okta](https://www.okta.com/) is the single sign-on mechanism. Each Okta
user is bound to a Box App User — an account that exists only inside your
application and has no Box login of its own — using `external_app_user_id`
to store the Okta `sub` claim. From then on, one Okta user always resolves
to one Box user, and you call the Box API as that person rather than as
your application.

This is the companion repository to the tutorial:
**[Connect Okta identities to Box App Users](https://developer.box.com/tutorials/connect-okta-to-app-users)**.

To keep the focus on the identity flow, the app has no user interface. It
returns plain text to the browser.

## What it does

| Capability | How |
| --- | --- |
| Sign in with Okta | OpenID Connect Authorization Code via `flask_oidc` |
| Look up the Box App User | `GET /2.0/users?external_app_user_id={sub}` |
| Provision on first sign-in | `POST /2.0/users` with `is_platform_access_only` |
| Act as that user | CCG `with_user_subject`, then `GET /2.0/users/me` |

The app prints `New user created: {{USERNAME}}` on the first sign-in and
`Hello {{USERNAME}}` on every sign-in after that.

## Project layout

```
box-okta-connection/
├── server.py                       # Flask app, OIDC routes, Box lookup/provision
├── config.py.example               # Flask session key + Box CCG credentials
├── client_secrets.json.example     # Okta OIDC client ID, secret, issuer
├── requirements.txt
├── .gitignore
└── LICENSE
```

Copy the example files to `config.py` and `client_secrets.json` before
running. Both hold secrets and are gitignored.

## Prerequisites

- **Python 3.11+**
- A [free Box developer account](https://account.box.com/signup/developer),
  with Developer Console access. An enterprise admin must
  authorize the Platform App — app user calls fail until it is authorized.
- An Okta [Integrator Free Plan org](https://developer.okta.com/docs/reference/org-defaults/)
  with administrator rights. Starting from a new org avoids disturbing
  existing app integrations and users.
- A **Client Credentials Grant (CCG)** Platform App, **authorized** in the
  Admin Console, with:
  - Application scopes: **Read and write all files and folders stored in
    Box** and **Manage Users**
  - **Additional Configuration**: **Generate user access tokens** enabled

## Setup

1. **Clone and enter the project**

   ```bash
   git clone https://github.com/box-community/box-okta-connection.git
   cd box-okta-connection
   ```

2. **Create a virtual environment and install dependencies**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   ```

   Install exactly one Box package: `boxsdk` v10 or later. Do not also
   install `box-sdk-gen` — both ship the `box_sdk_gen` module and conflict.

3. **Create the Okta app integration**

   If you do not have an Okta org yet, go to the
   [Okta sign-up page](https://developer.okta.com/signup/) and select
   **Sign up for Integrator Free Plan** in the Okta Workforce Identity tile.
   An Integrator Free Plan org allows up to 10 active users and deactivates
   after 180 consecutive days with no sign-ins.

   If you sign in and land on the end-user dashboard, select **Admin** in
   the upper-right corner to reach the Admin Console.

   Go to **Applications and Resources** > **Applications**, then select
   **Create App Integration**. Choose **OIDC - OpenID Connect** and **Web
   Application**, then:

   - **Grant types**: **Authorization Code** only
   - **Sign-in redirect URIs**: `http://127.0.0.1:5000/authorize`
   - **Sign-out redirect URIs**: `http://127.0.0.1:5000/`
   - **Assignments**: leave **Everyone**, or select the group that holds
     your test user

   `/authorize` is where Flask-OIDC receives the response from Okta. The
   connector also registers `/login` and `/logout`.

   Nobody can sign in unless they are assigned to the integration. If you
   narrowed **Assignments**, assign the test user after you create them.

4. **Copy Okta credentials**

   ```bash
   cp client_secrets.json.example client_secrets.json
   ```

   Fill in `client_id` and `client_secret` from **Client Credentials** on
   the integration's **General** tab. Set `issuer` to `https://` + your
   Okta domain + `/oauth2/default`. The domain is in the username
   drop-down in the Admin Console (for example `dev-123456.okta.com`).

   ```json
   {
     "web": {
       "client_id": "OKTA CLIENT ID",
       "client_secret": "OKTA CLIENT SECRET",
       "issuer": "https://dev-123456.okta.com/oauth2/default"
     }
   }
   ```

   The issuer is the only Okta URL you provide. Flask-OIDC reads
   `{issuer}/.well-known/openid-configuration` at sign-in time and
   discovers the authorization, token, and user info endpoints from it.

   > **Never commit `client_secrets.json`.** It is already in `.gitignore`.

5. **Create a test Okta user**

   In the Admin Console, go to **Directory** > **People** > **Add person**.
   Enter a first name, last name, and username in email format — Okta
   combines first and last name into the `name` claim used for the Box
   user's name. For **Password**, select **I will set password**, enter a
   password, and clear **User must change password on first login**.

   If you narrowed **Assignments**, open the integration's **Assignments**
   tab and assign this user.

   Setting a password as the administrator and skipping the password change
   is for testing only.

6. **Configure and authorize the Box application**

   1. Go to the [Developer Console](https://app.box.com/developers/console).
   2. Select **New App**, enter a name, choose **Server** and **Client
      Credentials Grant (CCG)**, then **Create**.
   3. Enable **Read and write all files and folders stored in Box** and
      **Manage Users**.
   4. Enable **Generate user access tokens**.
   5. Select **Save**.

   A new application cannot call the Box API until an enterprise admin
   authorizes it. Follow
   [platform app approval](https://developer.box.com/guides/authorization/platform-app-approval).
   After you change scopes or advanced features, reauthorize the app so
   the change takes effect.

   ```bash
   cp config.py.example config.py
   ```

   Fill in the three Box SDK values. The client ID and client secret are
   in **App Details** on the **Configuration** tab (viewing the client
   secret requires two-factor authentication). The enterprise ID is in
   **Properties** on the same tab. `flask_secret_key` signs Flask session
   cookies — any long random string works.

   ```python
   flask_secret_key = 'a-long-random-string-for-session-signing'
   box_client_id = 'YOUR_BOX_CLIENT_ID'
   box_client_secret = 'YOUR_BOX_CLIENT_SECRET'
   box_enterprise_id = 'YOUR_BOX_ENTERPRISE_ID'
   ```

   > **Never commit `config.py`.** It is already in `.gitignore`.

   To reuse an existing CCG application, confirm the same three things on
   its **Configuration** page: CCG as the authentication method, the two
   scopes above, and **Generate user access tokens** enabled.

## Run

Activate the virtual environment first, then start Flask through Python so
the `flask` executable does not need to be on your `PATH`:

```bash
source .venv/bin/activate
python -m flask --app server.py run
```

Flask reports that it is running on `http://127.0.0.1:5000/`. Open that
address in a browser. Because no one is signed in yet, Flask-OIDC sends
you to the Okta sign-in form.

Sign in with the test user. On the first sign-in, no Box user carries that
Okta ID yet, so the app creates one and the browser displays:

```text
New user created: Test User
```

Reload the page. This time the lookup finds the Box user, the app acts as
them, and the browser displays:

```text
Hello Test User
```

Seeing the second message confirms the whole chain: Okta authenticated
the person, Box resolved them to an App User, and the app called the Box
API with a token scoped to that user.

To run the sign-in from the beginning again, go to
`http://127.0.0.1:5000/logout` to clear the session, then open
`http://127.0.0.1:5000/` once more.

## How it works

1. A visitor requests `/` and is redirected to `/box_auth`.
2. `@oidc.require_login` sends anyone who is not signed in to Okta. The
   `openid profile` scopes return the permanent `sub` ID and the `name`
   claim.
3. `Box.validate_user` searches enterprise users for
   `external_app_user_id` equal to that `sub`. Use `sub` rather than
   username or email — it never changes, so renaming someone in Okta does
   not strand their Box account.
4. If no match exists, `create_user` provisions an App User
   (`is_platform_access_only=True`) and stamps the same `sub` onto it.
5. If a user exists, `authenticate_as_user` requests a
   [user-scoped CCG token](https://developer.box.com/guides/authentication/client-credentials)
   with `with_user_subject` and calls `users.get_user_me()` to confirm it.

The lookup is what makes the flow repeatable. Because
`external_app_user_id` is stored on the Box user and is searchable, the
app never needs its own mapping table.

## Security notes

- Keep the Box client secret, Okta client secret, and Flask session key
  server-side. Do not commit `config.py` or `client_secrets.json`.
- App Users belong to your application and cannot sign in to Box
  directly. Grant only the scopes this sample needs (**Manage Users**
  plus read/write files, and **Generate user access tokens**).
- Serve the app over HTTPS anywhere other than your own machine, and
  update the Okta **Sign-in redirect URIs** to the `https://` address at
  the same time.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Okta rejects the sign-in or redirects to an error page | Confirm **Sign-in redirect URIs** is exactly `http://127.0.0.1:5000/authorize`, including the port, and that **Authorization Code** is selected. **Reports** > **System Log** in the Admin Console records each failed attempt with a reason. |
| Okta signs the user in but denies access to the app | Open the integration's **Assignments** tab and confirm the person is assigned, either directly or through a group. |
| The connector cannot reach the Okta endpoints | Open `{issuer}/.well-known/openid-configuration` in a browser. If it does not return JSON, `issuer` in `client_secrets.json` is wrong. The most common mistakes are omitting `/oauth2/default` or leaving off the `https://` prefix. |
| Box user created with a missing or wrong name | Confirm `OIDC_SCOPES` is `'openid profile'`, then sign out and sign in again. Also confirm the test user in Okta has both a first and last name. |
| Box rejects the user search or user creation | Authorize the app in the Admin Console, or enable **Manage Users** and reauthorize. |
| `invalid_grant` / Box client cannot authenticate | Confirm `box_client_id`, `box_client_secret`, and `box_enterprise_id` in `config.py`. A typo in any of the three values returns `invalid_grant`. |
| A new Box user is created on every sign-in | Confirm `create_user` sets `external_app_user_id` to the `sub` claim and that `validate_user` searches for that same value. |
| Acting as the user fails, even though the user exists | Enable **Generate user access tokens**, save, then reauthorize the app. |
| `ModuleNotFoundError: config` | Copy `config.py.example` to `config.py` and fill in your Box credentials. |
| `ModuleNotFoundError` for Flask or Box | Activate the venv: `source .venv/bin/activate`. Install with `pip install -r requirements.txt` (uses boxsdk only — do not also install `box-sdk-gen`). |

## Scaling to production

- Load credentials from environment variables or a secrets manager rather
  than files on disk. Generate the Flask session key randomly per
  deployment.
- Resolve the Box user once per session and cache the ID, so the
  enterprise-user search runs only at first sign-in.
- Give new App Users the folder structure and collaborations they need at
  creation time. See
  [user provisioning](https://developer.box.com/guides/users/provision/index)
  and
  [provisioning architecture](https://developer.box.com/guides/users/provision/architecture).
- When someone is deactivated in Okta,
  [deprovision](https://developer.box.com/guides/users/deprovision/index)
  the Box account and
  [transfer their content](https://developer.box.com/guides/users/deprovision/transfer-folders).
- App Users suit applications where Box is invisible to the person using
  it. If users also need to sign in to Box directly, use
  [connecting existing identities](https://developer.box.com/guides/sso-identities-and-app-users/connect-identities)
  to create managed users instead.

## Related

- Tutorial: [Connect Okta identities to Box App Users](https://developer.box.com/tutorials/connect-okta-to-app-users)
- [SSO and App Users](https://developer.box.com/guides/sso-identities-and-app-users)
- [Create an App User](https://developer.box.com/guides/sso-identities-and-app-users/create-app-user)
- [Find an App User](https://developer.box.com/guides/sso-identities-and-app-users/find-app-user)
- [Connect existing identities](https://developer.box.com/guides/sso-identities-and-app-users/connect-identities)
- [Client Credentials Grant](https://developer.box.com/guides/authentication/client-credentials)
- [Platform app approval](https://developer.box.com/guides/authorization/platform-app-approval)

## License

[MIT](./LICENSE)
