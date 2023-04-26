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

def fsave(fname, txt, bin_mode=False): # Txt files only!
    os.makedirs(abs_path(os.path.dirname(fname)), exist_ok=True)
    if type(txt) is str:
        with open(fname, mode='w', encoding="utf-8") as file_obj:
            file_obj.write(txt.replace('\r\n','\n'))
    elif type(txt) is bytes:
        with open(fname, mode='wb') as file_obj:
            file_obj.write(txt)
    else:
        raise Exception('Can only save strings and bytes.')

def fload(fname, bin_mode=False): # Code adapted from Termpylus
    if not os.path.isfile(fname):
        return None
    if bin_mode:
        with io.open(fname, mode="rb") as file_obj:
            return file_obj.read()
    else:
        with io.open(fname, mode="r", encoding="utf-8") as file_obj:
            try:
                x = file_obj.read()
            except UnicodeDecodeError:
                raise Exception('No UTF-8 for:', fname)
            out = x.replace('\r\n','\n')
            return out

def fdelete():
    if os.path.exists(fname):
        os.path.unlink(fname)

def folder_load(folder_path, initial_path=None, allowed_extensions=None, acc=None):
    # filename => values.
    if acc is None:
        acc = {}
    if initial_path is None:
        initial_path = folder_path
    for filename in os.listdir(folder_path):
        fname = folder_path+'/'+filename
        if os.path.isdir(fname):
            folder_load(fname, initial_path, allowed_extensions, acc)
        else:
            if allowed_extensions is not None:
                if '.' not in filename or filename.split('.')[-1] not in allowed_extensions:
                    continue
            acc[fname[len(initial_path):]] = fload(fname)

    return acc

def power_delete(filder, ignore_permiss_error=False):
    import stat
    def del_rw(action, name, exc): #https://stackoverflow.com/questions/21261132/shutil-rmtree-to-remove-readonly-files
        os.chmod(name, stat.S_IWRITE)
        os.remove(name)
    try:
        if os.path.isfile(filder) or os.path.islink(filder):
            os.unlink(filder)
        elif os.path.isdir(filder):
            shutil.rmtree(filder, onerror=del_rw)
    except PermissionError as e:
        if not ignore_permiss_error:
            raise e

def empty_folder(folder, ignore_permiss_error=False, keeplist=None):
    # Useful for installation, since actually deleting the folder can cause problems.
    # https://stackoverflow.com/questions/185936/how-to-delete-the-contents-of-a-folder
    if not os.path.exists(folder):
        os.makedirs(folder)
        return
    for filename in os.listdir(folder):
        if keeplist is not None and filename in keeplist:
            continue
        power_delete(folder+'/'+filename, ignore_permiss_error)

def copy_with_overwrite(folderA, folderB, ignore_permiss_error=False):
    #Everything in folderA ends up in folderB. Files and folders with the same name are deleted first.
    filesb = set(os.listdir(folderB))
    for fname in os.listdir(folderA):
        filderB = folderB+'/'+fname
        if fname in filesb:
            power_delete(filderB, ignore_permiss_error=True)
        if not os.path.exists(filderB): # Still may exist when ignore_permiss.
            if os.path.isfile(folderA+'/'+fname):
                shutil.copyfile(folderA+'/'+fname, filderB)
            else:
                shutil.copytree(folderA+'/'+fname, filderB)

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
