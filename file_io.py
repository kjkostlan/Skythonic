# File IO functions.
import os, io, pickle, codecs, shutil

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

def empty_folder(folder, ignore_permiss_error=False):
    # Useful for installation, since actually deleting the folder works.
    import stat
    def del_rw(action, name, exc): #https://stackoverflow.com/questions/21261132/shutil-rmtree-to-remove-readonly-files
        os.chmod(name, stat.S_IWRITE)
        os.remove(name)
    # https://stackoverflow.com/questions/185936/how-to-delete-the-contents-of-a-folder
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path, onerror=del_rw)
        except PermissionError as e:
            if not ignore_permiss_error:
                raise e

def pickle64(x):
    # Pickles all the Python files (with UTF-8), or changed ones with diff.
    # Updates the _last_pickle so only use when installing.
    #https://stackoverflow.com/questions/30469575/how-to-pickle-and-unpickle-to-portable-string-in-python-3
    return codecs.encode(pickle.dumps(x), "base64").decode()

def disk_unpickle64(txt64):
    # Saves to the disk, deletes None files. Pickle can handle local paths.
    fname2obj = pickle.loads(codecs.decode(txt64.encode(), "base64"))
    for fname, txt in fname2obj.items():
        if txt is None:
            try:
                os.remove(fname)
            except:
                print('Warning: file deletion during update failed for',fname)
        else:
            fsave(fname, txt) # auto-makes enclosing folders.
    print('Saved to these files:', fname2obj.keys())
