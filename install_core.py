# Core installation and realtime updating features.
# Some code is copied from kjkostlan/Termpylus with slight adaptions.
import io, sys, os, importlib
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

def src_cache_diff():
    # Changed file local path => contents; deleted files map to None
    current = src_cache_from_disk(); past = _src_cache
    out = {}
    for k in past.keys():
        if k not in current:
            out[k] = None
    for k in current.keys():
        if current[k] != past.get(k,None):
            out[k] = current[k]
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

try:
    _src_cache
except:
    _src_cache = {}
    update_src_cache()
    print(f'Initalized _src_cache with {len(_src_cache)} files (app startup).')

############################# Pickling for a portable string ###################

def disk_pickle(diff=False):
    # Pickles all the Python files (with UTF-8), or changed ones with diff.
    # Updates the _last_pickle so only use when installing.
    delta = src_cache_diff() if diff else src_cache_from_disk()
    for k in delta.keys():
        if k[0]=='/':
            raise Exception('Absolute-like filepath in the src cache (bug in this file).')
    print('Pickling these:', delta.keys())
    return file_io.pickle64(delta)

def unpickle_and_update(txt64, update_us=True, update_vms=True):
    file_io.disk_unpickle64(txt64)

    delta = src_cache_diff()
    if update_us:
        update_python_interp(delta)
    if update_vms:
        import vm # delay the import because install_core has to run as standalone for fresh installs.
        vm.update_vms_skythonic(delta)
    update_src_cache() # Update this also.
