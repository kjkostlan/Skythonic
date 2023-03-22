# File IO functions.
import os, io, pickle, codecs

def abs_path(fname): # Code from Termpylus
    return os.path.abspath(fname).replace('\\','/')

def rel_path(fname): # Will default to abs_path if not inside this folders (less messy than double dots).
    a = abs_path(fname)
    ph = abs_path(os.path.dirname(os.path.realpath(__file__))) #https://stackoverflow.com/questions/5137497/find-the-current-directory-and-files-directory
    nthis_folder = len(ph)

    if ph in a:
        return ('./'+a[nthis_folder:]).replace('//','/')
    else:
        return a

def fsave(fname, txt): # Txt files only!
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

def pickle64(x):
    # Pickles all the Python files (with UTF-8), or changed ones with diff.
    # Updates the _last_pickle so only use when installing.
    #https://stackoverflow.com/questions/30469575/how-to-pickle-and-unpickle-to-portable-string-in-python-3
    return codecs.encode(pickle.dumps(x), "base64").decode()

def disk_unpickle64(txt64):
    # Saves to the disk, deletes None files. Pickle can handle lcoal paths.
    fname2obj = pickle.loads(codecs.decode(txt64.encode(), "base64"))
    for fname, txt in fname2obj.items():
        if txt is None:
            try:
                os.remove(fname)
            except:
                print('Warning: file deletion during update failed for',fname)
        else:
            file_io.fsave(fname, txt) # auto-makes enclosing folders.
    print('Saved to these files:', fname2obj.keys())
    delta = src_cache_diff()
    if update_us:
        update_python_interp(delta)
    if update_vms:
        import vm # delay the import because install_core has to run as standalone for fresh installs.
        vm.update_vms_skythonic(delta)
    update_src_cache() # Update this also.
