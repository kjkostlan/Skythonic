# Paste this into the AWS cloud shell to install. Go line-by-line or all at once.
# There is no indentation since that would interfere with the paste-in.
# Lave the skythonic() function will automatically run everything.
python3=1 # Bash/python polyglot fun (works whether you are Python or bash, and leaves the CLI in Python).
python3
import os, sys, importlib
branch="dev"
root = 'https://raw.githubusercontent.com/kjkostlan/Skythonic/' + branch + '/'
files = ['AWS_core.py','AWS_clean.py','AWS_setup.py','AWS_query.py']
module_strs = [file.replace('.py','').replace('/','.') for file in files]
f0 = lambda: [os.remove(file) for file in files] # Curl doesn't overwrite (I think).
f1 = lambda: [os.system(' '.join(['curl','-o',f,root+f])) for f in files]
import1 = lambda mdname: setattr(sys.modules['__main__'], mdname, __import__(mdname))
f2 = lambda: [import1(mdname) for mdname in module_strs] #https://stackoverflow.com/questions/301134/how-can-i-import-a-module-dynamically-given-its-name-as-string
f3 = lambda: [importlib.reload(sys.modules[mdname]) for mdname in module_strs]
skythonic = lambda:[f0(), f1(), f2(), f3()]
skythonic()
ls = lambda: os.system('ls') # TODO: better check if it worked.
print('Installation hopefully worked!')
