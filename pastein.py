# Install these python tools with a single Ctrl+V:
#    python; import pastein; pastein.install(windows=False, diff=False/True)
# Then just paste these into your python-capable cloud shell (or Jumpbox shell, etc).
# (Python must be version 3)
# Once you have it installed? Call awsP(), etc to add useful fns to your Python shell.
import sys, time
import install_core

def _importcode(mnames):
    return ['import '+mname for mname in mnames]

def _joinlines(lines, windows=False):
    if windows:
        out = '\r\n'+'\r\n'.join(lines)+'\r\n'
    else:
        out = '\n'+'\n'.join(lines)+'\n'
    return out

def install(windows=False, diff=False):
    import clipboard #pip install clipboard on your machine, no need on the Cloud Shell.

    lines = ['python3=3','python3','python=3','python'] # In or out of python shell.

    if not diff: # Diff will only change the differences.
        lines.append('import sys, os, time, subprocess')
        boot_txt = install_core.fload('install_core.py')
        lines.append('pyboot_txt=r"""'+boot_txt+'"""') # works because no triple """ in boot_txt.
        lines.append('pyboot_f_obj = open("install_core.py","w")')
        lines.append('pyboot_f_obj.write(pyboot_txt)')
        lines.append('pyboot_f_obj.close()')

    big_txt = install_core.disk_pickle(diff)
    lines.append('obj64 = r"""'+big_txt+'"""')
    if diff:
        lines.append('install_core.disk_unpickle(obj64, True)')
    else:
        lines.append('import install_core')
        lines.append('install_core.disk_unpickle(obj64)')
        lines.append('from pastein import *')

    clipboard.copy(_joinlines(lines, windows))
    print("Copied installation to clipboard!")

def awsP(windows=False):
    imports = ['AWS.AWS_core as AWS_core','AWS.AWS_clean as AWS_clean','AWS.AWS_setup as AWS_setup','AWS.AWS_query as AWS_query', 'boto3']
    lines = _importcode(imports)
    lines = lines+["ec2r = boto3.resource('ec2')", "ec2c = boto3.client('ec2')", 'who = AWS_query.get_resources']
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

def azureP(windows=False):
    lines = [] # TODO
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

def googleP(windows=False):
    lines = [] # TODO
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

# All these below are lower prority (<=5%)
#https://www.statista.com/chart/18819/worldwide-market-share-of-leading-cloud-infrastructure-service-providers/
def alibabaP(windows=False):
    lines = [] # TODO
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

def ibmP(windows=False):
    lines = [] # TODO
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

def salesforceP(windows=False):
    lines = [] # TODO
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

def tencentP(windows=False):
    lines = [] # TODO
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

def oracleP(windows=False):
    lines = [] # TODO
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

if __name__ == '__main__': # For running on your local machine.
    fresh = 1
    while True:
        if fresh==0:
            x = input('If you made changes press enter to load them to clipboard; press "a" to load everything').lower().strip()
        else:
            x = input('Press enter to load the project into the clipboard as well as useful imports.').lower().strip()
        if x=='q':
            quit()
        diff = fresh==0 and x !='a'
        n = len(install_core.pickle_file_dict(diff))
        if n==0:
            print('No files changed')
        else:
            install(windows=False, diff=diff)
            x = input('Your clipboard is ready with: '+str(n)+' pickled files; press enter once pasted in.')
        fresh = 0