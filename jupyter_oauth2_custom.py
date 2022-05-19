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
    import asdc

    await asdc.auth.connect()

    asdc.download('/projects/{PID}/tasks/{TID}/download/{ASSET}')

    """.format(PID=project, TID=task, ASSET=asset)

    from pathlib import Path
    with open(str(Path.home() / filename), 'w') as f:
        f.write(content)

    if redirect == 'yes':
        self.redirect("/user-redirect/lab/tree/" + filename)
    else:
        request.write(filename)


