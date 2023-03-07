# Paste this into the AWS cloud shell to install. Go line-by-line or all at once.
python3=1 # Bash/python polyglot fun (works whether you are Python or bash, and leaves the CLI in Python).
python3
import os
branch="dev"
root = 'https://raw.githubusercontent.com/kjkostlan/Skythonic/' + branch + '/'
files = ['AWS_core.py','AWS_clean.py','AWS_install.py','AWS_setup.py','AWS_query.py']
[os.system(' '.join(['curl','-o',f,root+f])) for f in files]
ls = lambda : os.system('ls')
