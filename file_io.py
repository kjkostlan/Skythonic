# File IO functions.
import os, io

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
