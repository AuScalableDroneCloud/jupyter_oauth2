# https://jupyter-server-proxy.readthedocs.io/en/latest/server-process.html

def setup_jupyter_oauth2():
  return {
    'command': ['python', '-m', 'jupyter_oauth2_server', '{port}', '{base_url}'],
  }


