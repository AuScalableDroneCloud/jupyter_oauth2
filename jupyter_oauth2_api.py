"""
# OAuth2 login in Jupyter Notebooks

This module provides a way to login to an oauth2 provider and get an access_token from inside a jupyter environment

It has only been tested on the Auth0 provider for the Australian Scalable Drone Cloud project,
If it will work with other providers and scenarios is not known.

- Borrows code from and uses same techniques as ipyauth (https://oscar6echo.gitlab.io/ipyauth/) but without the widget
- Use popup or iframe to send the request 
- Listen for callback with a custom server behind jupyter-server-proxy - this provides a stable URL to configure as
  a callback at https://MY-JUPYTERHUB/jupyterhub_oauth2/callback, this is required by Auth0 as we can't have a wildcard port
  in the configured callback url.
- Receive token with another server behind jupyter-server-proxy within the calling environment,
  allowing user API calls to get/use the token

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

#Pass the config dict above (this can also be loaded from environment variables)
auth.setup(config)

#Connect to the OAuth2 provider, default is to open a new window for the login
auth.connect()

#Display info about a logged in user
auth.showuserinfo()

#Call an API with GET
r = asdc.auth.call_api('/projects/')
print(r.json())

#Call an API with POST
data = {'name': 'My Project', 'description': 'Created by API with token'}
r = asdc.auth.call_api('/projects/', data)
print(r.json())

```

### ipyauth 

https://oscar6echo.gitlab.io/ipyauth/guide/install.html

- works in notebook if server extension installed correctly
- does not work in lab, widget incompatible with jupyterlab 3 https://gitlab.com/oscar6echo/ipyauth/-/issues/8
- requires the callback to be registered on Auth0 App (eg: http://localhost:8888/callback/) wildcards are supported in subdomains only

## See also

https://auth0.com/docs/libraries/auth0-single-page-app-sdk this sdk uses Authorization code flow with PKCE (designed for native and single page apps), possibly more secure for this case https://auth0.com/docs/authorization/flows/authorization-code-flow-with-proof-key-for-code-exchange-pkce

"""

import requests
import json
import os
import logging

baseurl = ''      #Base jupyterhub url
access_token = '' #Store the received token here
token_data = ''   #All the received token data
port = None       #Server port, default is to automatically assign
nonce = ''        #For verifying token

#Settings, to be provided before use
settings = {
    "default_baseurl": 'https://JUPYTERHUB_URL/user-redirect',
    "api_audience": 'https://MYSITE/api',
    "api_client_id": 'CLIENT_ID_HERE',
    "api_scope": 'openid profile email',
    "api_authurl": 'MY_OAUTH2_PROVIDER_URL',
    "provided" : False
}

def setup(config=None):
    global settings
    """Pass a dict with the authentication settings
    """
    if config is None:
        #Try and load from env variables
        try:
            settings["default_baseurl"] = os.getenv('JUPYTERHUB_URL') + '/user-redirect'
            settings["api_audience"] = os.getenv('JUPYTER_OAUTH2_API_AUDIENCE')
            settings["api_client_id"] = os.getenv('JUPYTER_OAUTH2_CLIENT_ID')
            settings["api_scope"] = os.getenv('JUPYTER_OAUTH2_SCOPE', 'openid profile email')
            settings["api_authurl"] = os.getenv('JUPYTER_OAUTH2_AUTH_PROVIDER_URL')
            settings["provided"] = True
        except Exception as e:
            print(e)
    else:
        settings = config
        settings["provided"] = True

def check_settings():
    if not settings['provided']:
        print('Please call .setup(dict) to configure before use, defaults are not usable:\n', settings)
        raise(Exception('Settings not provided'))

def get_url():
    """Can we automatically get the base url? Not without callback from the browser client
    This needs to be set in env var ideally, can be overridden by settings above
    """
    global settings, baseurl
    check_settings()
    import subprocess
    import json
    import os
    
    #Get from env if set
    server_url = os.getenv('JUPYTER_URL')
    if server_url:
        baseurl = server_url + '/user-redirect'
    else:
        result = subprocess.run('jupyter notebook list --json'.split(), stdout=subprocess.PIPE)
        res = result.stdout.decode().split('\n')

        #Just take the longest path that is above os.getcwd() - not 100% reliable though
        cwd = os.getcwd()
        lastlen = 0
        for r in res:
            if not len(r): break
            nbc = json.loads(r)
            d = nbc["notebook_dir"]
            if d in cwd and len(d) > lastlen:
                nbconfig = nbc
                lastlen = len(d)
        nbconfig
        if nbconfig['hostname'] == '0.0.0.0':
            #Default for ASDC
            baseurl = settings["default_baseurl"]
        else:
            #For localhost
            baseurl = nbconfig['url']
            if baseurl[-1] == '/':
                baseurl = baseurl[0:-1] #Remove trailing /
    logging.info("Base url: ", baseurl)

def serve():
    """
    Listen for the token passed by browser on client side
    
    See: https://notebook.community/knowledgeanyhow/notebooks/hacks/Webserver%20in%20a%20Notebook
    """
    global settings, port, token_data
    import tornado.ioloop
    import tornado.web
    import tornado.httpserver

    def set_token(data, verify=True):
        global nonce, token_data
        logging.debug("Verfifying, nonce: ", nonce, ", verify enabled: ",verify)
        if verify and data['id_token']['nonce'] != nonce:
            logging.error("INVALID TOKEN! Nonce does not match")
            token_data = None
        else:
            if verify:
                logging.debug("==> TOKEN VALIDATED!")
            else:
                logging.debug("==> TOKEN Reused, already validated")
            token_data = data

    class MainHandler(tornado.web.RequestHandler):
        def get(self):
            #'''Renders the template with a title on HTTP GET.'''
            #self.finish(page.render(title='Tornado Demo'))
            #Just confirm server is running
            self.finish('OK')

    class TokenHandler(tornado.web.RequestHandler):
        def post(self):
            import json
            data = self.request.body
            t = json.loads(data)
            logging.debug("==> TOKEN RECEIVED via POST")
            set_token(t)
            self.finish("Token processed")

        def get(self):
            import json
            import base64
            logging.debug("==> TOKEN RECEIVED via GET")
            data = self.get_argument("data", default=None, strip=False)
            t = json.loads(base64.b64decode(data).decode('utf-8'))
            if "/reusetoken" in self.request.uri:
                set_token(t, False) #Can't verify as nonce may have been cleared
            else:
                set_token(t) #Verify nonce
            self.finish("Token processed")

    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/token", TokenHandler),
        (r"/reusetoken", TokenHandler)
    ])

    #Selects a random port by default,
    #allowing multiple notebooks to use this without conflicts
    server = tornado.httpserver.HTTPServer(application)
    server.listen(port, '0.0.0.0')
    
    #Get the actual port assigned
    if port is None:
        #(First entry in _sockets)
        socket = server._sockets[next(iter(server._sockets))]
        port = socket.getsockname()[1]

    logging.debug("Running on port: ", port) 
    
    return server

async def check_server(url):
    """
    Test a server is working
    """
    logging.info("Testing url: ", url)
    
    import requests
    r = requests.get(U)

    if r.status_code >= 400:
        print(r.status_code, r.reason)
        raise(Exception("Failed to get a response from server!"))
    else:
        print(r.status_code, r.reason)
        print(r.text)
        print('Server is responding')

def listener(mode='popup'):
    """ Open auth request page with iframe / popup / link and listen for postMessage 
    
    mode='popup' opens page in new window/tab (may require disabling popup blockers)
    mode='iframe' opens page in inline iframe (this seems less reliable)
    mode='link' displays link to the auth page without opening it automatically
    """
    global settings, baseurl, port, access_token, token_data
    if not baseurl: get_url()
    from IPython.display import display, HTML
    
    from string import Template
    temp_obj = Template("""
    <script>
    //Have the token, send back to server with HTTP POST
    function postToken(data) {
        var xhr = new XMLHttpRequest();
        xhr.open("POST", '$BASEURL/proxy/$PORT/token', true);
        //Send the proper header information along with the request
        xhr.setRequestHeader("Content-Type", "application/json");
        xhr.onload = function() {console.log('postToken successful');}
        xhr.send(JSON.stringify(data));
    }

    //Have the token, send back to server with HTTP GET
    function postTokenGET(data, reuse) {
        var xhr = new XMLHttpRequest();
        var encoded = window.btoa(JSON.stringify(data));
        var uri = '$BASEURL/proxy/$PORT/token?data=' + encoded;
        if (reuse)
            uri = '$BASEURL/proxy/$PORT/reusetoken?data=' + encoded;
        xhr.open("GET", uri);
        xhr.onload = function() {console.log('postTokenGET successful');}
        xhr.send();
    }

    //Get message from iframe or popup
    function message_received(event) {
        //console.log("ORIGIN:" + event.origin);
        //console.log("MESSAGE:" + JSON.stringify(event.data));
        if ("access_token" in event.data) {
            //Save token on client side
            window.token = event.data;

            //POST gets 405 method not allowed on jupyterhub
            //postToken(event.data);
            postTokenGET(event.data);

            //Stop listening after sending token
            window.removeEventListener('message', self);
            //window.listenerExists = false;
        }
    }
    window.addEventListener("message", message_received);
    </script>
    """)
    script = temp_obj.substitute(BASEURL=baseurl, PORT=str(port))
    display(HTML(script))
    
    import urllib
    #This uses jupyter-server-proxy entry-point magic to provide a consistent callback url
    #(package jupyter_oauth2 must be installed: pip install git+https://github.com/AuScalableDroneCloud/jupyter_oauth2.git)
    redirect = baseurl + '/jupyter_oauth2/callback'
    import secrets
    global nonce
    nonce = secrets.token_urlsafe(nbytes=8)
    f = {'response_type' : 'token id_token',
         'redirect_uri' : redirect,
         'client_id' : settings["api_client_id"],
         'audience' : settings["api_audience"],
         'scope' : settings["api_scope"],
         'nonce' : nonce,
         'state' : 'auth0,' + nonce,
         #'state' : 'auth0,iframe,' + nonce,
         #'state' : 'auth0,popup,' + nonce,
         #'prompt' : 'none'}
        }
    logging.debug("Auth query params: ", f)
    #print("Auth query params: ", f)
    query = urllib.parse.urlencode(f)

    authurl = settings["api_authurl"] + '/authorize?' + query

    if mode == 'popup':
        from IPython.display import HTML
        from string import Template
        temp_obj = Template("""<script>
        var now = new Date().valueOf();
        if (window.token) console.log(window.token['id_token']['exp']*1000 + ' > ' + now);
        if (window.token && window.token['id_token']['exp']*1000 > now) {
            //Use saved token on client side
            postTokenGET(window.token, true); //Pass reuse flag to skip verification
        } else {
           window.open("$URL");
        }
        </script>""")
        script = temp_obj.substitute(URL=authurl)
        display(HTML(script))
    elif mode == 'link':
        display(HTML('<h3><a href="{url}" target="_blank" rel="opener">Click here to login to ASDC</a></h3>'.format(url=authurl)))
    elif mode == 'iframe':
        from IPython.display import IFrame
        display(IFrame(authurl, 0, 0))
        #display(IFrame(url, 400, 300))

async def connect():
    """Start the server, call the auth api and await token
    """
    global settings, access_token, token_data
    check_settings()
    server = serve()
    listener()
    
    import asyncio
    import time
    import sys
    print('Waiting for authorisation', end='')
    for i in range(1,150): #~30 seconds
        if token_data: break
        await asyncio.sleep(0.1)
        print('.', end='')
        sys.stdout.flush()
        time.sleep(0.1)
    
    if not token_data:
        raise(Exception("Timed out awaiting access token!"))
    else:
        print('.. Success.')

    access_token = token_data['access_token']
    
    #Stop the server
    await server.close_all_connections()
    server.stop()

def call_api(url, data=None, throw=False):
    global access_token
    if url[0:4] != "http":
        #Prepend the configured api url
        url = settings["api_audience"] + url
    #WebODM api call
    headersAPI = {
    'accept': 'application/json',
    'Content-type': 'application/json',
    'Authorization': 'Bearer ' + access_token if access_token else '',
    }
    
    #POST if data provided, otherwise GET
    if data:
        r = requests.post(url, headers=headersAPI, json=data)
    else:
        r = requests.get(url, headers=headersAPI)
    
    if r.status_code >= 400:
        print(r.status_code, r.reason)
        if throw:
            raise(Exception("Error response from server!"))
    #print(r.text)
    return r

def call_api_js(url, callback="alert()", data=None):
    #GET, list nodes, passing url and token from python
    from IPython.display import display, HTML
    #Generate a code to prevent this call happening again if page reloaded without clearing
    import string
    import secrets
    alphabet = string.ascii_letters + string.digits
    code = "req_" + ''.join(secrets.choice(alphabet) for i in range(8))
    method = "POST"
    if data is None:
        method = "GET"
        data = {}
    from string import Template
    temp_obj = Template("""<script>
    //Prevent multiple calls
    if (!window._requests) 
      window._requests = {};
    if (!window._requests["$CODE"]) {
        var data = $DATA;
        var callback = $CALLBACK;
        var xhr = new XMLHttpRequest();
        xhr.open("$METHOD", "$URL");
        xhr.setRequestHeader("Authorization", "Bearer $TOKEN");
        //Can also just grab it from window...
        //xhr.setRequestHeader("Authorization", "Bearer " + window.token['access_token']);
        xhr.responseType = 'json';
        xhr.onload = function() {
            // Request finished. Do processing here.
            var data = xhr.response;
            console.log('success');
            callback(xhr.response);
        }

        if (data && Object.keys(data).length) {
            var formData = new FormData();
            for (var key in data)
                formData.append(key, data[key]);

            xhr.send(formData);
        } else {
            xhr.send();
        }

        //Flag request sent
        window._requests["$CODE"] = true;
    }
    </script>
    """)
    script = temp_obj.substitute(DATA=json.dumps(data),
                CODE=code, METHOD=method, URL=url,
                TOKEN=access_token, CALLBACK=callback)
    display(HTML(script))

def userinfo():
    r = call_api(settings["api_authurl"] + '/userinfo')
    data = r.json()
    return data

def showuserinfo():
    user = userinfo()
    #print(json.dumps(user, indent=4, sort_keys=True))
    print("Username: ", user["name"])
    from IPython.display import display, HTML
    display(HTML("<img src='" + user["picture"] + "' width='120' height='120'>"))

