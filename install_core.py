# Core installation and realtime updating features.
# Some code is copied from kjkostlan/Termpylus with slight adaptions.
import io, sys, os, codecs, pickle, importlib

############################# File operations ##################################

def abs_path(fname): # Code from Termpylus
    return os.path.abspath(fname).replace('\\','/')

def rel_path(fname):
    a = abs_path(fname)
    ph = abs_path(os.path.dirname(os.path.realpath(__file__))) #https://stackoverflow.com/questions/5137497/find-the-current-directory-and-files-directory
    nthis_folder = len(ph)
    return ('./'+a[nthis_folder:]).replace('//','/')

def fsave(fname, txt):
    os.makedirs(abs_path(os.path.dirname(fname)), exist_ok=True)
    with open(fname, mode='w', encoding="utf-8") as file_obj:
        file_obj.write(txt.replace('\r\n','\n'))

def fload(fname): # Code adapted from Termpylus
    if not os.path.isfile(fname):
        return None
    with io.open(fname, mode="r", encoding="utf-8") as file_obj:
        try:
            x = file_obj.read()
        except UnicodeDecodeError:
            raise Exception('No UTF-8 for:', fname)
        out = x.replace('\r\n','\n')
        return out

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
                fnamer = rel_path(os.path.join(root, fname))
                fname2contents[fnamer] = fload(fnamer)
    return fname2contents

def src_cache_diff():
    # Changed file local path => contents; deleted files map to None
    current = src_cache_from_disk(); past = _src_cache
    out = {}
    for k in past.keys()
        if k not in current:
            out[k] = None
    for k in current.keys():
        if current[k] != past.get(k,None):
            out[k] = current[k]
    return out

def update_src_cache(): # Also returns which modules changed (only modules which were already in module_fnames).
    sc1 = src_cache_from_disk()
    for k in _src_cache.keys():
        del _src_cache[k]
    for k in sc1.keys():
        _src_cache[k] = sc1[k]

def module_fnames: # code from Termpylus.
    # Only modules that have files, and dict values are module names.
    # Also can restrict to user-only files.
    out = {}
    for k in sys.modules.keys():
        fname = sys.modules[k].__dict__.get('__file__', None)
        if fname is not None:
            out[k] = fname.replace('\\','/')
    return out

def update_python_interp():
    fnames = module_fnames()
    delta = src_cache_diff()
    changed_modules = TODO # get modulename from filename with __file__
    for m in changed_modules:
        update_one_module(m, fnames[m])

try:
    _src_cache
except:
    print('Initializing _src_cache (app startup).')
    _src_cache = {}
    update_src_cache()

############################# Pickling for a portable string ###################

def disk_pickle(diff=False):
    # Pickles all the Python files (with UTF-8), or changed ones with diff.
    # Updates the _last_pickle so only use when installing.
    cache = src_cache_diff() if diff else src_cache_from_disk()
    print('Pickling these:', save_these.keys())
    #https://stackoverflow.com/questions/30469575/how-to-pickle-and-unpickle-to-portable-string-in-python-3
    return codecs.encode(pickle.dumps(save_these), "base64").decode()

def disk_unpickle(txt64, update_us=True, update_vms=True):
    #https://stackoverflow.com/questions/30469575/how-to-pickle-and-unpickle-to-portable-string-in-python-3
    fname2obj = pickle.loads(codecs.decode(txt64.encode(), "base64"))
    for fname, txt in fname2obj.items():
        if fname[0]=='/': # Relative paths need to not start with '/'
            fname = fname[1:]
        if txt is None:
            try:
                os.remove(fname)
            except:
                print('Warning: file deletion during update failed for',fname)
        else:
            fsave(fname, txt) # auto-makes enclosing folders.
    if update_us:
        update_python_interp()
    if update_vms:
        import vm # delay the import because install_core has to run as standalone for fresh installs.
        vm.update_vms_skythonic(src_cache_diff())
    update_src_cache() # Update this also.
