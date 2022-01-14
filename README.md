# jupyter_oauth2

Get an oauth2 token to access api, based on ipyauth

Based heavily on ipyauth: https://gitlab.com/oscar6echo/ipyauth

This bypasses the need for a widget, which is broken in ipyauth in latest jupyterlab.

Because there is no widget for user interaction, the login can be done in an iframe or an invisible iframe if the user guaranteed to already be logged in to the oauth2 provider

(eg: for single sign-on where jupyter is running behind same oauth2 login)

The jupyter-server-proxy package is required and this module must be installed before the jupyter server is started (so if you run pip install from within a notebook on the server, it will not work)
