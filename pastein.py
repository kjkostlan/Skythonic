# Uses Python pickling to generate a cut-and-past installer.
# (these auto-set the clipboard).
'''
import pastein
pastein.aws()
'''
import clipboard #clipboard.copy('foo'); pip install clipboard

def _common():
    out = ['python3=3','python3','python=3','python'] # In or out of python shell.
    big_txt = install_core.disk_pickle()
    out.append('contents = r"""'+big_txt+'"""')
    out.append('import install_core')
    out.append('install_core.disk_unpickle()')
    return out

def _importcode(mnames):
    return ['import '+mname for mname in mnames]

def aws():
    lines = common()+_importcode('AWS.AWS_core as AWS_core','AWS.AWS_clean as AWS_clean','AWS.AWS_setup as AWS_setup','AWS.AWS_query as AWS_query')
    out = '\n'+'\n'.join(lines)+'\n'
    clipboard.copy(out)
    return out

def azure():
    lines = common()
    out = '\n'+'\n'.join(lines)+'\n'
    clipboard.copy(out)
    return out

def google():
    lines = common()
    out = '\n'+'\n'.join(lines)+'\n'
    clipboard.copy(out)
    return out

# All these below are lower prority (<=5%)
#https://www.statista.com/chart/18819/worldwide-market-share-of-leading-cloud-infrastructure-service-providers/
def alibaba():
    TODO
    c = common()
    return '\n'+'\n'.join(out)+'\n'

def ibm():
    lines = common()
    out = '\n'+'\n'.join(lines)+'\n'
    clipboard.copy(out)
    return out

def salesforce():
    lines = common()
    out = '\n'+'\n'.join(lines)+'\n'
    clipboard.copy(out)
    return out

def tencent():
    lines = common()
    out = '\n'+'\n'.join(lines)+'\n'
    clipboard.copy(out)
    return out

def oracle():
    lines = common()
    out = '\n'+'\n'.join(lines)+'\n'
    clipboard.copy(out)
    return out
