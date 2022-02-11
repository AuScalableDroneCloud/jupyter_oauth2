import setuptools

setuptools.setup(
  name="jupyter_oauth2",
  # py_modules rather than packages, since we only have a few files
  py_modules=['jupyter_oauth2', 'jupyter_oauth2_server', 'jupyter_oauth2_api'],
  entry_points={
      'jupyter_serverproxy_servers': [
          # name = packagename:function_name
          'jupyter_oauth2 = jupyter_oauth2:setup_jupyter_oauth2',
      ]
  },
  install_requires=['jupyter-server-proxy', 'pillow', 'qrcode'],
)
