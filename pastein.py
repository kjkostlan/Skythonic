# Install these python tools with a singl Ctrl+V:
#    import pastein; pastein.install()
# Then just paste these into your python-capable cloud shell (or Jumpbox shell, etc).
# (Python must be version 3)
# Once you have it installed? Call aws(), then Ctrl+v to get useful commands!

import clipboard #pip install clipboard
import install_core

def _importcode(mnames):
    return ['import '+mname for mname in mnames]

def _joinlines(lines, windows=False):
    if windows:
        out = '\r\n'+'\r\n'.join(lines)+'\r\n'
    else:
        out = '\n'+'\n'.join(lines)+'\n'
    return out

def install(windows=False): # Install in linux.
    lines = ['python3=3','python3','python=3','python'] # In or out of python shell.

    boot_txt = install_core.fload('install_core.py')
    lines.append('pyboot_txt=r"""'+boot_txt+'"""') # works because no triple """ in boot_txt.
    lines.append('pyboot_f_obj = open("install_core.py","w")')
    lines.append('pyboot_f_obj.write(boot_txt)')
    lines.append('pyboot_f_obj.close()')

    big_txt = install_core.disk_pickle()
    lines.append('obj64 = r"""'+big_txt+'"""')
    lines.append('import install_core')
    lines.append('install_core.disk_unpickle(obj64)')
    lines.append('from pastein import *')

    clipboard.copy(_joinlines(lines, windows))

def awsP(windows=False):
    imports = ['AWS.AWS_core as AWS_core','AWS.AWS_clean as AWS_clean','AWS.AWS_setup as AWS_setup','AWS.AWS_query as AWS_query', 'boto3']
    lines = _importcode(imports)
    lines = lines+["ec2r = boto3.resource('ec2')", "ec2c = boto3.client('ec2')", 'who = AWS_query.get_resources']
    clipboard.copy(_joinlines(lines, windows))

def azureP(windows=False):
    lines = [] # TODO
    clipboard.copy(_joinlines(lines, windows))

def googleP(windows=False):
    lines = [] # TODO
    clipboard.copy(_joinlines(lines, windows))

# All these below are lower prority (<=5%)
#https://www.statista.com/chart/18819/worldwide-market-share-of-leading-cloud-infrastructure-service-providers/
def alibabaP(windows=False):
    lines = [] # TODO
    clipboard.copy(_joinlines(lines, windows))

def ibmP(windows=False):
    lines = [] # TODO
    clipboard.copy(_joinlines(lines, windows))

def salesforceP(windows=False):
    lines = [] # TODO
    clipboard.copy(_joinlines(lines, windows))

def tencentP(windows=False):
    lines = [] # TODO
    clipboard.copy(_joinlines(lines, windows))

def oracleP(windows=False):
    lines = [] # TODO
    clipboard.copy(_joinlines(lines, windows))
