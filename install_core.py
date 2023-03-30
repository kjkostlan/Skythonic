# Core installation and realtime updating features.
# Some code is copied from kjkostlan/Termpylus with slight adaptions.
import io, sys, os, importlib, shutil
import file_io

########################### Modules and updating ###############################

def clear_pycache(filename): # Code adapted from Termpylus.
    # This can intefere with updating.
    cachefolder = os.path.dirname(filename)+'/__pycache__'
    leaf = os.path.basename(filename).replace('.py','')
    printouts = True
    if os.path.isdir(cachefolder):
        leaves = os.listdir(cachefolder)
        for l in leaves:
            if leaf in l:
                if printouts:
                    print('Deleting cached file:', cachefolder+'/'+l)
                os.remove(cachefolder+'/'+l)

def update_one_module(modulename, fname):
    # Updates a module that is already loaded (unloaded modules don't need).
    clear_pycache(fname) # Clear before updating.
    try:
        importlib.reload(sys.modules[modulename])
        print('Updating MODULE:', modulename)
    except Exception as e:
        print('Updating FAILURE:', modulename, repr(e))

def src_cache_from_disk():
    # Gets the src cache from the disk, filename => contetns with local cache.
    # Looks for all python files within this directory.
    fname2contents = {}
    for root, dirs, files in os.walk(".", topdown=False): # TODO: exclude .git and __pycache__ if the time cost becomes significant.
        for fname in files:
            if fname.endswith('.py'):
                fnamer = file_io.rel_path(os.path.join(root, fname))
                fname2contents[fnamer] = file_io.fload(fnamer)
    return fname2contents

def src_cache_diff(old_cache=None, new_cache=None):
    # Changed file local path => contents; deleted files map to None
    if old_cache is None:
        old_cache = _src_cache
    if new_cache is None:
        new_cache = src_cache_from_disk()

    out = {}
    for k in old_cache.keys():
        if k not in new_cache:
            out[k] = None
    for k in new_cache.keys():
        if new_cache[k] != old_cache.get(k,None):
            out[k] = new_cache[k]
    for k in old_cache.keys():
        if k[0]=='/':
            raise Exception('Absolute-like filepath in the src cache (bug in this function).')
    return out

def update_src_cache(new_cache=None): # Also returns which modules changed (only modules which were already in module_fnames).
    if new_cache is None:
        new_cache = src_cache_from_disk()
    for k in list(_src_cache.keys()):
        del _src_cache[k]
    for k in new_cache.keys():
        _src_cache[k] = new_cache[k]

def module_fnames(): # code from Termpylus.
    # Only modules that have files, and dict values are module names.
    # Also can restrict to user-only files.
    out = {}
    for k in sys.modules.keys():
        fname = sys.modules[k].__dict__.get('__file__', None)
        if fname is not None:
            out[k] = fname.replace('\\','/')
    return out

def update_python_interp(delta):
    # Keep the Python intrepretator up to date
    fnames = module_fnames()
    inv_fnames = dict(zip([file_io.rel_path(v) for v in fnames.values()], fnames.keys()))
    for fname in delta.keys():
        if fname in inv_fnames:
            mname = inv_fnames[fname]
            if mname in sys.modules:
                update_one_module(inv_fnames[fname], fname)

def replace_with_Git_fetch(branch='main', folder='.'):
    # Uses git fetch. WARNING: removes everything in folder.
    if os.path.exists(folder):
        file_io.empty_folder(folder, ignore_permiss_error=True)
    else:
        os.makedirs(folder, exist_ok=True)
    if os.path.exists(folder+'/install_core.py'):
        raise Exception('Folder not cleaned in preparation for GitHub fetch.')
    os.system(f'git clone -b "{branch}" "https://github.com/kjkostlan/Skythonic" "{folder}"')
    if not os.path.exists(folder+'/install_core.py'):
        raise Exception('Files not created; likely non-existant Git branch or Git not installed.')

try:
    _src_cache
except:
    _src_cache = {}
    update_src_cache()
    print(f'Initalized _src_cache with {len(_src_cache)} files (app startup).')

############################# Pickling for a portable string ###################

def unpickle_and_update(txt64, update_us=True, update_vms=True):
    file_io.disk_unpickle64(txt64)
    delta = src_cache_diff()
    if update_us:
        update_python_interp(delta)
    if update_vms:
        try:
            import vm # delay the import because install_core has to run as standalone for fresh installs.
            vm.update_vms_skythonic(delta)
        except ModuleNotFoundError:
            print('Cant update the vms because vm hasent been downloaded yet.')
    update_src_cache()

############################ Bootstrapping an installation #####################

def joinlines(lines, windows=False):
    if windows:
        out = '\r\n'+'\r\n'.join(lines)+'\r\n'
    else:
        out = '\n'+'\n'.join(lines)+'\n'
    return out

def bootstrap_txt(windows, pickle64, pyboot_txt=True, import_txt=True, github_txt=False):
    lines = ['python3=3','python3','python=3','python'] # In or out of python shell.
    quote3 = "''"+"'" # Can't appear in file.

    if pyboot_txt: # Diff will only change the differences.
        lines.append('import sys, os, time, subprocess')
        for py_file in ['install_core.py', 'file_io.py']:
            boot_txt = file_io.fload(py_file)
            varname = py_file[0:-3]+'_src'
            if quote3 in boot_txt:
                raise Exception('This ad-hoc paste-in system cannot handle files with triple single quotes.')
            lines.append(f'{varname}=r{quote3}{boot_txt}{quote3}') # works because no triple """ in boot_txt.
            lines.append(f'pyboot_f_obj = open("{py_file}","w")')
            lines.append(f'pyboot_f_obj.write({varname})')
            lines.append('pyboot_f_obj.close()')
    lines.append(f'obj64 = r"""{pickle64}"""')
    if import_txt:
        lines.append('import install_core')
    lines.append('install_core.unpickle_and_update(obj64, True, True)')
    if github_txt: # This is an interactive tool => use dev branch.
        lines.append("import install_core")
        #lines.append("sudo apt-get install git") # Would this help to have?
        lines.append("install_core.replace_with_Git_fetch(branch='dev', folder='.')")
    if import_txt:
        lines.append('from pastein import *')
    return joinlines(lines, windows)
