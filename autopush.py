# Automatically push to GitHub, but only if there is a change.
# (Autopush is needed b/c we curl from the GitHub).
import os, subprocess, time

def push_if_change():
    #https://stackoverflow.com/questions/1685157/how-can-i-specify-working-directory-for-a-subprocess
    #https://stackoverflow.com/questions/3503879/assign-output-of-os-system-to-a-variable-and-prevent-it-from-being-displayed-on
    #https://stackoverflow.com/questions/5137497/find-the-current-directory-and-files-directory
    this_folder = os.path.dirname(os.path.realpath(__file__))
    proc = subprocess.Popen(["git", "status"], stdout=subprocess.PIPE, shell=True, cwd=this_folder)
    (out, err) = proc.communicate()
    print('Out is:', out)
    #os.system('git push https://github.com/kjkostlan/Skythonic')

while True:
    push_if_change()
    time.sleep(1)
