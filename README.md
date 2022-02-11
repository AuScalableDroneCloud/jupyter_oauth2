# jupyter_oauth2

Get an OAuth2 token to access an API

Based on ideas/code in ipyauth: https://gitlab.com/oscar6echo/ipyauth

This bypasses the need for a widget, which is broken in ipyauth in latest jupyterlab.

Because there is no widget for user interaction, the login can be done in an iframe or an invisible iframe if the user guaranteed to already be logged in to the oauth2 provider

(eg: for single sign-on where jupyter is running behind same oauth2 login)

The jupyter-server-proxy package is required and must be installed (along with this package) BEFORE the jupyter server is started (ie: if you use !pip install jupyter_oauth2 from within a notebook on the server, it will not work as the server extension requires a restart)


# OAuth2 login in Jupyter Notebooks

This module provides a way to login to an OAuth2 provider and get an id_token and access_token from inside a Jupyter notebook environment.

It has only been tested on the Auth0 provider for the ASDC (Australian Scalable Drone Cloud) project, if it will work with other providers and scenarios is not known.

- Borrows code from and uses same techniques as ipyauth (https://oscar6echo.gitlab.io/ipyauth/) but without the widget
- Use popup or iframe to send the request 
- Listen for callback with a custom server behind jupyter-server-proxy - this provides a stable URL to configure as
  a callback at https://MY-JUPYTERHUB/jupyterhub_oauth2/callback, this is required by Auth0 as we can't have a wildcard port
  in the configured callback url.
- Receive token with another server behind jupyter-server-proxy within the calling environment,
  allowing user API calls to get/use the token

See "How it works" below for a more detailed run through.

## Usage

```
import jupyter_oauth2_api as auth

config = {
    "default_baseurl": 'https://JUPYTERHUB_URL/user-redirect',
    "api_audience": 'https://MYSITE/api',
    "api_client_id": 'CLIENT_ID_HERE',
    "api_scope": 'openid profile email',
    "api_authurl": 'MY_OAUTH2_PROVIDER_URL',
}

# Connect to the OAuth2 provider, default is to open a new window for the login
# Pass the config dict above (this can also be loaded from environment variables
# by not passing in a config dict, see the code for the variable names)
await auth.connect(config)

# Display info about a logged in user
auth.showuserinfo()

# Call an API with GET
r = auth.call_api('/projects/')
print(r.json())

# Call an API with POST
data = {'name': 'My Project', 'description': 'Created by API with token'}
r = auth.call_api('/projects/', data)
print(r.json())
```

### Device Auth Flow

An alternative method is the Device Auth Flow which allows authenticating from a device that is not in a browser,
or running in a non-authenticated or logged in context, it requires more user interaction as the user must follow
a link and then confirm an 8 character code. If the qrcode module is installed a QR code can also be displayed
for easier authentication via a mobile device.

For Auth0 this requires a Native API app with the device flow enabled.

Thanks to Joe Parks for making me aware of this and providing the example code here:
https://gitlab.com/oscar6echo/ipyauth/-/issues/8#note_837687415

```
import jupyter_oauth2_api as auth

config = {
    "api_audience": 'https://MYSITE/api',
    "api_client_id": 'CLIENT_ID_HERE',
    "api_scope": 'openid profile email',
    "api_authurl": 'MY_OAUTH2_PROVIDER_URL',
}

# Connect to the OAuth2 provider and generate a link for the user to authenticate
# Pass the config dict above (this can also be loaded from environment variables
# by not passing in a config dict, see the code for the variable names)
await auth.device_connect(config)

```

### ipyauth 

This was all influenced / based on the ipyauth tool by Olivier Borderies, but this is no longer maintained.

https://oscar6echo.gitlab.io/ipyauth/guide/install.html

- works in basic notebook if server extension installed correctly
- does not work in jupyterlab, as widget is incompatible with jupyterlab 3 https://gitlab.com/oscar6echo/ipyauth/-/issues/8
- requires the callback to be registered on Auth0 App (eg: http://localhost:8888/callback/),
  this is tricky because wildcards are supported in subdomains only so we would only be able to support a few predefined port numbers.

## How it works

1. jupyter-server-proxy allows servers to be proxied behind the jupyter web server, eg: service running on https://ourdomain.tld:8080 can now be accessed on https://ourdomain.tld/proxy/8080. This also works in jupyterhub via the /user-redirect (https://jupyter-server-proxy.readthedocs.io/en/latest/)

2. Because we need to register the callback for our Auth0 app, we need a fixed url rather than using a dynamic port number. An entrypoint to jupyter_server_proxy is defined which ties a given url to an application to run on the command line. (See: https://jupyter-server-proxy.readthedocs.io/en/latest/server-process.html#specifying-config-from-python-packages)
This is used to define the url /jupyter_oauth2 which will start a tornado web server process on a new port which handles all requests directed to that url. This url can now be provided to Auth0 as the callback: https://ourdomain.tld/user-redirect/jupyter_oauth2/callback for JupyterHub or http://localhost/jupyter_oauth2/callback for running locally. Thanks to the entrypoint magic we don't need to know the port number.

3. The callback server itself is defined in jupyter_oauth2_server.py, it contains the token extraction Javascript and HTML from ipyauth and serves it on the path /callback.
When the authentication flow is complete the JWT id_token is extracted and this along with access_token and other details are send back to the parent/calling window via postMessage.

4. In a Jupyter Notebook, we can now start the authentication flow by opening our auth url in a popup window or iframe. We listen for the 'message' event to receive the token with Javascript on the client/browser and if all goes well recieve it as a JSON object, but this is not enough: we need the token on the server for use in python!

5. To get the token on the server side, we have started ANOTHER tornado web server, again with a random unused port number (although mentioned last, this is actually the first step in the implemention). Upon receiving the token data, the browser then passes it back to the server side using an ajax GET request, again via jupyter-server-proxy, using the port number we got from tornado when the server was started, eg: https://ourdomain.tld/user-redirect/proxy/PORT/token?data=encoded_token_data.

6. That's it! Because the aforementioned server is running in the same python context as the notebook, the token data can now simply be read from python.

## See also, OAuth2

Disclaimer: I am not an expert in this stuff, the code needs to be audited for security.

The authorisation flow used is derived from ipyauth as it was the best example I could get working in testing.

Only the client_id is sent (no client_secret, although we could put in an env var on the server if necessary). The id_token is returned in the get request query to the callback url. The access_token is returned as a fragment (#access_token) so has to be accessed in the browser/Javascript as it never reaches the server.

This does not seem to match up with any flows here https://auth0.com/docs/get-started/authentication-and-authorization-flow/which-oauth-2-0-flow-should-i-use

Seems most similar to: https://auth0.com/docs/get-started/authentication-and-authorization-flow/implicit-flow-with-form-post, but according to this it is for an id_token only. We are able to get an access_token, is this a loophole that will be closed at some point?

This seems the most appropriate, but we are not doing this full flow: https://auth0.com/docs/libraries/auth0-single-page-app-sdk . The js SDK uses Authorization code flow with PKCE (designed for native and single page apps), probably more secure for this case https://auth0.com/docs/authorization/flows/authorization-code-flow-with-proof-key-for-code-exchange-pkce

Noting here as at some point we may need to add the PKCE steps.

