# https://jupyter-server-proxy.readthedocs.io/en/latest/server-process.html

def setup_jupyter_oauth2():
  return {
    'command': ['python3', 'jupyter_oauth2_server.py', '{port}', '{base_url}'],
  }


