# Uses Python pickling to generate a cut-and-past installer.
# (these auto-set the clipboard).
'''
import pastein
pastein.aws()
'''
import clipboard #clipboard.copy('foo'); pip install clipboard
import install_core

def _common():
    out = ['python3=3','python3','python=3','python'] # In or out of python shell.

    boot_txt = install_core.fload('install_core.py')
    out.append('boot_txt=r"""'+boot_txt+'"""') # works because no triple """ in boot_txt.
    out.append('boot_f_obj = open("install_core.py","w")')
    out.append('boot_f_obj.write(boot_txt)')
    out.append('boot_f_obj.close()')

    big_txt = install_core.disk_pickle()
    out.append('obj64 = r"""'+big_txt+'"""')
    out.append('import install_core')
    out.append('install_core.disk_unpickle(obj64)')
    return out

def _importcode(mnames):
    return ['import '+mname for mname in mnames]

def aws():
    lines = _common()+_importcode(['AWS.AWS_core as AWS_core','AWS.AWS_clean as AWS_clean','AWS.AWS_setup as AWS_setup','AWS.AWS_query as AWS_query'])
    out = '\n'+'\n'.join(lines)+'\n'
    clipboard.copy(out)
    return out

def azure():
    lines = _common()
    out = '\n'+'\n'.join(lines)+'\n'
    clipboard.copy(out)
    return out

def google():
    lines = _common()
    out = '\n'+'\n'.join(lines)+'\n'
    clipboard.copy(out)
    return out

# All these below are lower prority (<=5%)
#https://www.statista.com/chart/18819/worldwide-market-share-of-leading-cloud-infrastructure-service-providers/
def alibaba():
    lines = _common()
    out = '\n'+'\n'.join(lines)+'\n'
    clipboard.copy(out)
    return out

def ibm():
    lines = _common()
    out = '\n'+'\n'.join(lines)+'\n'
    clipboard.copy(out)
    return out

def salesforce():
    lines = _common()
    out = '\n'+'\n'.join(lines)+'\n'
    clipboard.copy(out)
    return out

def tencent():
    lines = _common()
    out = '\n'+'\n'.join(lines)+'\n'
    clipboard.copy(out)
    return out

def oracle():
    lines = _common()
    out = '\n'+'\n'.join(lines)+'\n'
    clipboard.copy(out)
    return out
