# Paste this into the AWS cloud shell to install. Go line-by-line or all at once.
# There is no indentation since that would interfere with the paste-in.
python3=1 # Bash/python polyglot fun (works whether you are Python or bash, and leaves the CLI in Python).
python3
import os
branch="dev"
root = 'https://raw.githubusercontent.com/kjkostlan/Skythonic/' + branch + '/'
files = ['AWS_core.py','AWS_clean.py','AWS_install.py','AWS_setup.py','AWS_query.py']
skythonic = lambda: [os.system(' '.join(['curl','-o',f,root+f])) for f in files]
skythonic()
ls = lambda: os.system('ls')
module_strs = [file.replace('.py','').replace('/','.')]
[__import__(mdname) for mdname in module_strs] #https://stackoverflow.com/questions/301134/how-can-i-import-a-module-dynamically-given-its-name-as-string
print('Installation hopefully worked!')
