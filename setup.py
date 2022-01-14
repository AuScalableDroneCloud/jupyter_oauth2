import setuptools

setuptools.setup(
  name="jupyter-oauth2-server",
  # py_modules rather than packages, since we only have 1 file
  py_modules=['jupyter_oauth2', 'jupyter_oauth2_server'],
  entry_points={
      'jupyter_serverproxy_servers': [
          # name = packagename:function_name
          'jupyter_oauth2 = jupyter_oauth2:setup_jupyter_oauth2',
      ]
  },
  install_requires=['jupyter-server-proxy'],
)
