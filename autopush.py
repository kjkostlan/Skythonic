# Automatically push to GitHub, but only if there is a change.
# (Autopush is needed b/c we curl from the GitHub).
import os, subprocess, time

def call_proc(args):
    #https://stackoverflow.com/questions/5137497/find-the-current-directory-and-files-directory
    this_folder = os.path.dirname(os.path.realpath(__file__))
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, shell=True, cwd=this_folder)
    (out, err) = proc.communicate()
    out = '' if out is None else out.decode('UTF-8')
    err = '' if err is None else err.decode('UTF-8')
    return out, err

def push_if_change():
    #https://stackoverflow.com/questions/1685157/how-can-i-specify-working-directory-for-a-subprocess
    #https://stackoverflow.com/questions/3503879/assign-output-of-os-system-to-a-variable-and-prevent-it-from-being-displayed-on

    out, err = call_proc(["git", "status"])
    if 'nothing to commit, working tree clean' in out:
        print('No commits needed.')
    elif 'On branch dev' not in out:
        print('Not on branch dev, this script can only work if on branch dev.')
    else:
        x = input('Commits needed, input message: ')
        outa, erra = call_proc(["git", "add", "*"])
        outc, errc = call_proc(["git", "commit", "-m", x])
        print("Commit:", outc, errc)
        outp, errp = call_proc(["git", "push", '"https://github.com/kjkostlan/Skythonic"'])
        print("Commit:", outp, errp)

while True:
    push_if_change()
    time.sleep(1)
