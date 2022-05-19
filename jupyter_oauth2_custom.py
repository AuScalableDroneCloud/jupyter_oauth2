#This is a placeholder
def handler(request):
    """
    Additional functions can be added here

    eg:

    data = request.get_argument('data')
    request.write(data)
    """

    #Write a python module to import the selected task
    project = request.get_argument('project')
    task = request.get_argument('task')
    asset = request.get_argument('asset', 'orthophoto.tif')
    redirect = request.get_argument('redirect', 'yes')
    filename = 'task_{0}.py'.format(task)

    content = """
    # ---
    # jupyter:
    #   jupytext:
    #     text_representation:
    #       extension: .py
    #       format_name: light
    #       format_version: '1.5'
    #   kernel_info:
    #     name: python3
    #   kernelspec:
    #     display_name: Python 3
    #     language: python
    #     name: python3
    # ---

    # + [markdown] inputHidden=false outputHidden=false
    # # Loading a data set from ASDC WebODM
    #
    # This notebook / script will load a specific task dataset
    #

    # + inputHidden=false outputHidden=false
    import asdc

    await asdc.auth.connect(mode='iframe')

    project = '{PID}'
    task = '{TID}'
    filename = '{ASSET}'
    asdc.download(project, task, asset)

    """.format(PID=project, TID=task, ASSET=asset)

    from pathlib import Path
    with open(str(Path.home() / filename), 'w') as f:
        f.write(content)

    if redirect == 'yes':
        #self.redirect("/user-redirect/lab/tree/" + filename)
        self.redirect("https://jupyter.asdc.cloud.edu.au/user-redirect/lab/tree/" + filename)
    else:
        request.write("""
        <!DOCTYPE html>
        <html lang="en">

        <head>
            <meta charset="utf-8" />
            <title>ASDC API server</title>
        </head>

        <body>
            <h1>ASDC API Request</h3>
            <p>Request processed for {FN}
            <a href="https://jupyter.asdc.cloud.edu.au/user-redirect/lab/tree/{FN}">(Output here)</a>
            <a href="/user-redirect/lab/tree/{FN}">(Output here)</a>
            </p>
        </body>

        </html>
        """.format(FN=filename))

