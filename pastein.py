
import sys, time
import install_core, file_io

def _importcode(mnames):
    return ['import '+mname for mname in mnames]

def awsP(windows=False):
    imports = ['AWS.AWS_core as AWS_core','AWS.AWS_clean as AWS_clean','AWS.AWS_setup as AWS_setup','AWS.AWS_query as AWS_query', 'boto3']
    lines = _importcode(imports)
    lines = lines+["ec2r = boto3.resource('ec2')", "ec2c = boto3.client('ec2')", 'who = AWS_query.get_resources']
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

def azureP(windows=False):
    lines = [] # TODO
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

def googleP(windows=False):
    lines = [] # TODO
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

# All these below are lower prority (<=5%)
#https://www.statista.com/chart/18819/worldwide-market-share-of-leading-cloud-infrastructure-service-providers/
def alibabaP(windows=False):
    lines = [] # TODO
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

def ibmP(windows=False):
    lines = [] # TODO
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

def salesforceP(windows=False):
    lines = [] # TODO
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

def tencentP(windows=False):
    lines = [] # TODO
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

def oracleP(windows=False):
    lines = [] # TODO
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

if __name__ == '__main__': # For running on your local machine.
    import clipboard #pip install clipboard on your machine, no need on the Cloud Shell.

    while True:
        #install_txt(windows=False, diff=False, pyboot_txt=True, import_txt=True)
        x = input('Enter to load diffs into clipboard (a to not diff, q to quit)').lower().strip()
        if x=='q':
            quit()
        diff = x !='a'
        n = len(install_core.src_cache_diff() if diff else install_core.src_cache_from_disk())

        txt = install_core.bootstrap_txt(windows=False, diff=diff, pyboot_txt=(not diff), import_txt=True)
        new_cache = install_core.src_cache_from_disk()
        clipboard.copy(txt)
        if n==0:
            x = input('No pickled files, but press enter to paste in the import code to jumpstart your Python work.').lower().strip()
        else:
            x = input('Your clipboard is ready with: '+str(n)+' pickled files; press enter once pasted in or c to cancel').lower().strip()
        if x != 'c':
            install_core.update_src_cache(new_cache)
