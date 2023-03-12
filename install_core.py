# Core installation and realtime updating features.
# Some code is copied from kjkostlan/Termpylus with slight adaptions.
import io, sys, os, codecs, pickle

try:
    _src_cache
except:
    _src_cache = {}
    _last_pickle = {}

############################# File operations ##################################

def abs_path(fname): # Code from Termpylus
    return os.path.abspath(fname).replace('\\','/')

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

def module_file(m): # Code from Termpylus
    if type(m) is str:
        m = sys.modules[m]
    if '__file__' not in m.__dict__ or m.__file__ is None:
        return None
    return abs_path(m.__file__)

def module_fnames(): # Code adapted from Termpylus
    # Only modules inside our folder.
    out = {}
    dir_path = abs_path(os.path.dirname(os.path.realpath(__file__)))
    for k in sys.modules.keys():
        fname = module_file(sys.modules[k])
        if fname is not None and dir_path in fname:
            out[k] = fname.replace('\\','/')
    return out

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

def update_src_cache(): # Also returns which modules changed (only modules which were already loaded).
    mod_f = module_fnames()
    changed_modules = [] # Must be already loaded.
    for k, v in mod_f.items():
        txt = fload(v)
        if k in _src_cache and _src_cache[k] != txt:
            changed_modules.append(k)
        _src_cache[k] = txt
    return changed_modules

def update_changed_files():
    fnames = module_fnames()
    changed_modules = update_src_cache()
    for m in changed_modules:
        update_one_module(m, fnames[m])

if len(_src_cache)==0: # One time on startup to skip updating everything.
    update_src_cache()

############################# Pickling for a portable string ###################

def disk_pickle(diff=False):
    # Pickles all the Python files (with UTF-8), or changed ones with diff.
    nthis_fname = len(abs_path(os.path.dirname(os.path.realpath(__file__)))) #https://stackoverflow.com/questions/5137497/find-the-current-directory-and-files-directory

    fname2contents = {}
    for root, dirs, files in os.walk(".", topdown=False):
        for fname in files:
            if fname.endswith('.py'):
                fname1 = abs_path(os.path.join(root, fname))
                fname2contents[fname1] = fload(fname1)
    fname_local2contents = dict(zip([k[nthis_fname:] for k in fname2contents.keys()], [x for x in fname2contents.values()]))

    save_these = {}
    for k in fname_local2contents.keys():
        txt = fname_local2contents[k]
        if _last_pickle.get(k,None) != txt or not diff:
            save_these[k] = txt
            _last_pickle[k] = txt

    print('Pickling these:', save_these.keys())
    #https://stackoverflow.com/questions/30469575/how-to-pickle-and-unpickle-to-portable-string-in-python-3
    return codecs.encode(pickle.dumps(save_these), "base64").decode()

def disk_unpickle(txt64, update=True):
    #https://stackoverflow.com/questions/30469575/how-to-pickle-and-unpickle-to-portable-string-in-python-3
    fname2obj = pickle.loads(codecs.decode(txt64.encode(), "base64"))
    for fname, txt in fname2obj.items():
        if fname[0]=='/': # Relative paths need to not start with '/'
            fname = fname[1:]
        fsave(fname, txt) # auto-makes encloding folders.
    if update:
        update_changed_files()
