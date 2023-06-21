# Downloads projects from Github or a local folder.
import io, sys, os, shutil, stat, time

def _unwindoze_attempt(f, filename_err_report, tries=12, retry_delay=1, throw_some_errors=False):  # Duplicate code from file_io in the Waterworks repo.
    for i in range(tries):
        try:
            f()
            break
        except PermissionError as e:
            if 'being used by another process' in str(e):
                print('File-in-use error (will retry) for:', filename_err_report)
            else:
                if throw_some_errors:
                    f() # Throw actual permission errors.
                else:
                    print('Will retry because of this PermissionError:', str(e))

            if i==tries-1:
                raise Exception('Windoze error: Retried too many times and this file stayed in use:', filename_err_report)
            time.sleep(retry_delay)

def power_delete(fname, tries=12, retry_delay=1.0): # Duplicate code from file_io in the Waterworks repo with minor modifications.
    fname = os.path.realpath(fname) # Changed to use builtin fns.
    if not os.path.exists(fname):
        return
    #_update_checkpoints_before_saving(fname) # Line modified.

    if os.path.isdir(fname):  # Changed to use builtin fns.
        for root, dirs, files in os.walk(fname, topdown=False):
            for _fname in files:
                _fname1 = root+'/'+_fname
                def f():
                    os.chmod(_fname1, stat.S_IWRITE)
                _unwindoze_attempt(f, _fname1, tries, retry_delay)
        _unwindoze_attempt(lambda: shutil.rmtree(fname), fname, tries, retry_delay)
    else:
        _unwindoze_attempt(lambda: os.remove(fname), fname, tries, retry_delay)

def copy_with_overwrite(src_folder, dest_folder): # Duplicate code from file_io in the Waterworks repo.
    # Acts recursivly.
    os.makedirs(dest_folder, exist_ok=True)

    for y in os.listdir(src_folder):
        src_item = src_folder+'/'+y
        dest_item = dest_folder+'/'+y

        if os.path.isfile(src_item) and os.path.isfile(dest_item):
            with open(src_item, 'rb') as file:
                x0 = file.read()
            with open(dest_item, 'rb') as file:
                x1 = file.read()
            if x0 != x1:
                power_delete(dest_item)
                shutil.copy2(src_item, dest_item)
        elif os.path.isfile(src_item) and not os.path.isfile(dest_item):
            power_delete(dest_item)
            shutil.copy2(src_item, dest_item)
        elif os.path.isdir(src_item):
            copy_with_overwrite(src_item, dest_item)

def clear_pycaches(folder): # Duplicate code from file_io in the Waterworks repo.
    # Clears all the __pycache__ in the given folder.
    for pwd, dirs, files in os.walk(folder):
        if pwd.replace('\\','/').split('/')[-1] == '__pycache__':
            for fl in files:
                power_delete(fl)

def download(url, dest_folder, clear_folder=False, branch='main'):
    # Downloads a project to dest_folder. branch will only be used if there are branches.
    dest_folder = os.path.realpath(dest_folder)
    if os.path.exists(dest_folder) and clear_folder:
        power_delete(dest_folder)
    if os.path.exists(dest_folder):
        clear_pycaches(dest_folder)
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    qwrap = lambda txt: '"'+txt+'"'

    if '//github.com' in url or '//www.github.com' in url:
        if clear_folder:
            dest_folder1 = dest_folder+'/git_tmp_dump'
            power_delete(dest_folder1, tries=12, retry_delay=1.0)
            print('Fetching from GitHub')
            qwrap = lambda txt: '"'+txt+'"'
            cmd = ' '.join(['git','clone', '--branch', qwrap(branch), qwrap(url), qwrap(dest_folder1)])
            power_delete(dest_folder+'/.git')
            os.system(cmd) #i.e. git clone https://github.com/the_use/the_repo the_folder. os.system will wait for the cmd to finish.
            copy_with_overwrite(dest_folder1, dest_folder)
            power_delete(dest_folder1)
            print('Git Clones saved into this folder:', dest_folder)
        else:
            if os.path.exists(dest_folder+'/.git'):
                cmd = ' '.join(['git', 'pull', url, '--allow-unrelated-histories'])
                os.system(cmd)
                cmd = ' '.join(['git', 'checkout', branch])
                os.system(cmd)
            else:
                cmd = ' '.join(['git','clone', '--branch', qwrap(branch), qwrap(url), qwrap(dest_folder)])
                os.system(cmd)
    elif url.startswith('http'):
        raise Exception(f'TODO: support other websites besides GitHub; in this case {url}')
    elif url.startswith('ftp'):
        raise Exception('FTP requests not planned to be supported.')
    else:
        url = os.path.realpath(url)
        if url == dest_folder:
            raise Exception(f'The origin folder is equal to the destination folder (both are {dest_folder})')
        else:
            if not os.path.exists(url):
                raise Exception(f'The origin is a folder on a local machine: {url} but that folder does not exist.')
            copy_with_overwrite(url, dest_folder)
