import os, sys, time

#######################Different code depending on which package################

def awsP(windows=False):
    imports = ['AWS.AWS_core as AWS_core','AWS.AWS_clean as AWS_clean',\
               'AWS.AWS_query as AWS_query',\
               'AWS.AWS_format as AWS_format', \
               'boto3', 'vm', 'tests.vms_setup as vms_setup', 'tests.core_tests as core_tests']
    lines = _importcode(imports)
    lines = lines+["ec2r = boto3.resource('ec2')", "ec2c = boto3.client('ec2')", "iam = boto3.client('iam')", 'who = AWS_query.get_resources']
    for line in lines:
        exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

def azureP(windows=False):
    raise Exception('TODO')
    lines = [] # TODO
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

def googleP(windows=False):
    raise Exception('TODO')
    lines = [] # TODO
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

def commonsCloudP(windows=False): # This one is special in that it is customer-owned.
    raise Exception('TODO')
    lines = [] # TODO
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

# All these below are lower prority (<=5%) and are unlikely to ever be implemented....
#https://www.statista.com/chart/18819/worldwide-market-share-of-leading-cloud-infrastructure-service-providers/
def alibabaP(windows=False):
    raise Exception('TODO')
    lines = [] # TODO
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

def ibmP(windows=False):
    raise Exception('TODO')
    lines = [] # TODO
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

def salesforceP(windows=False):
    raise Exception('TODO')
    lines = [] # TODO
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

def tencentP(windows=False):
    raise Exception('TODO')
    lines = [] # TODO
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

def oracleP(windows=False):
    raise Exception('TODO')
    lines = [] # TODO
    exec(_joinlines(lines, windows), vars(sys.modules['__main__']))

####################### Non-platform specific code below########################

try: # Import file_io, with a download of waterworks if need be.
    from waterworks import file_io
except:
    import proj # Will download to local machine.
    from waterworks import file_io

def _joinlines(lines, windows=False):
    if windows:
        out = '\r\n'+'\r\n'.join(lines)+'\r\n'
    else:
        out = '\n'+'\n'.join(lines)+'\n'
    return out

def _src_diff(old_file2contents, new_file2contents):
    # Changed file local path => contents; deleted files map to None
    out = {}
    for k in old_file2contents.keys():
        if k not in new_file2contents:
            out[k] = None
    for k in new_file2contents.keys():
        if new_file2contents[k] != old_file2contents.get(k,None):
            out[k] = new_file2contents[k]
    for k in old_file2contents.keys():
        if k[0]=='/':
            raise Exception('Absolute-like filepath in the src-code-as-dict, but only relative paths will work in most cases.')
    return out

def install_us(branch='main'):
    # Fetches git in a temporary folder and copies the contents here.
    import proj
    import code_in_a_box
    clean_here = False # Extra cleanup. Not necessary?

    if clean_here:
        file_io.empty_folder('.', keeplist=proj.dump_folder)
    tmp_folder = f'{proj.dump_folder}/GitDump' # Need a tmp folder b/c Git pulls only work on empty folders.
    if not os.path.exists(tmp_folder):
        os.makedirs(tmp_folder, exist_ok=True)
    else:
        file_io.empty_folder(tmp_folder)
    url = 'https://github.com/kjkostlan/Skythonic/'
    code_in_a_box.download(url, tmp_folder, clear_folder=False, branch=branch)
    file_io.copy_with_overwrite(tmp_folder, '.')

def _gitHub_bootstrap_txt(branch='main'):
    txt = """
cd ~
mkdir Skythonic
cd ~/Skythonic
python3
python
import os
branch = 'BRANCH'
fnames = ['proj.py', 'pastein.py']
#os.system('sudo apt install curl -y') # Make sure curl is installed first!
urls = [f'https://raw.githubusercontent.com/kjkostlan/Skythonic/{branch}/{fname}' for fname in fnames]
[os.unlink('./'+fname) if os.path.exists(fname) else None for fname in fnames]
curl_cmds = [f'curl "{urls[i]}" -o "./{fnames[i]}"' for i in range(len(fnames))]
[os.system(curl_cmd) for curl_cmd in curl_cmds]
bad_fnames = list(filter(lambda fname: not os.path.exists(fname), fnames))
print('WARNING: the curl bootstrap may have failed.') if len(bad_fnames)>0 else None
print(f'Curled github bootstrap branch {branch} to folder {os.path.realpath(".")}; the GitHub curl requests may be a few minutes out of date.')
import proj # Installs the file_io.py which is needed by pastein.
import pastein
pastein.install_us(branch=branch)
    """.replace('BRANCH', branch)
    txt = txt.replace('\n','\r\n')
    return txt

def _get_update_txt(pickle64_string):
    txt = '''
cd ~ # Bash cmds will error if attempted inside Python shell, but lines after errors will still run.
mkdir Skythonic
cd ~/Skythonic
python3
python
import sys, os, time, subprocess
obj64 = r"""PICKLE"""
from waterworks import py_updater
py_updater.unpickle64_and_update(obj64, True, True)
    '''.replace('PICKLE', pickle64_string)
    txt = txt.replace('\n','\r\n')
    return txt

def _importcode(mnames):
    return ['import '+mname for mname in mnames]

if __name__ == '__main__': # For running on your local machine.
    import clipboard #pip install clipboard on your machine, no need on the Cloud Shell.

    while True:
        sourcecode_before_input = file_io.python_source_load()
        x = input('<None> = load diffs, gm = Github with main branch bootstrap, gd = Github with dev fetch bootstrap, q = quit:')
        x = x.lower().strip()
        if x=='q' or x=='quit()':
            quit()
        sourcecode_afr_input = file_io.python_source_load()
        source_diff = _src_diff(sourcecode_before_input, sourcecode_afr_input)

        if x == 'gd' or x == 'gm':
            branch = 'main' if x == 'gm' else 'dev'
            txt = _gitHub_bootstrap_txt(branch=branch)
            clipboard.copy(txt)
            print(f'Bootstrap ready using GitHub fetch ({branch} branch).')
        elif x == '' or not x:
            big_txt = file_io.pickle64(source_diff)
            txt = _get_update_txt(big_txt)
            clipboard.copy(txt)
            n = len(source_diff)
            if n==0:
                print('No pickled files but code has been copied to jumpstart your Python work.')
            else:
                print(f'Your clipboard is ready with: {n} pickled files; {list(source_diff.keys())}; press enter once pasted in.')

'''
# Installation script (Bash):
git clone -b main https://github.com/kjkostlan/Skythonic.git Skythonic

cd ~/Skythonic
python3
from AWS import AWS_setup
report = AWS_setup.setup_jumpbox(basename='jumpbox', subnet_zone='us-west-2c', user_name='BYOC')
'''
