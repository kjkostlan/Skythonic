# Paste this into the AWS cloud shell to install. Go line-by-line or all at once.
# There is *no indentation* since that would interfere with the paste-in.
# Run the skythonic() function will automatically run everything.
python3=1 # Bash/python polyglot fun (works whether you are Python or bash, and leaves the CLI in Python).
python3
download_py = False # False to not download (i.e. local changes).
import boto3 # Conventions followed.
ec2r = boto3.resource('ec2')
ec2c = boto3.client('ec2')
import os, sys, importlib, shutil, random, string
branch="dev"
root = 'https://raw.githubusercontent.com/kjkostlan/Skythonic/' + branch + '/'
files = ['AWS_core.py','AWS_clean.py','AWS_setup.py','AWS_query.py']
rand_txt = ''.join(random.choices(string.ascii_letters + string.digits, k=16)) #https://serverfault.com/questions/698077/does-curl-cache-requests
module_strs = [file.replace('.py','').replace('/','.') for file in files]
import1 = lambda mdname: setattr(sys.modules['__main__'], mdname, __import__(mdname))
f0 = lambda: shutil.rmtree('./__pycache__') if os.path.exists('./__pycache__') else False
f1 = lambda: [os.remove(file) if os.path.exists(file) else False for file in files] # Curl doesn't overwrite (I think).
#https://reqbin.com/req/c-dyugjcgf/curl-no-cache-example
f2 = lambda: [os.system(' '.join(['curl','-o',f, '-H','"Cache-Control: no-cache, no-store, must-revalidate"', root+f+'?'+rand_txt])) for f in files]
#f2 = lambda: [os.system(' '.join(['curl','-o',f,root+f+'?'+rand_txt])) for f in files]
f3 = lambda: [import1(mdname) for mdname in module_strs] #https://stackoverflow.com/questions/301134/how-can-i-import-a-module-dynamically-given-its-name-as-string
f4 = lambda: [importlib.reload(sys.modules[mdname]) for mdname in module_strs]
do = lambda f,g: g() if f() != '___' else None # do in order, which may be affecting the curl refreshing.
skythonicD = lambda: do(lambda: do(lambda: do(f0,f1), lambda: do(f2,f3)), f4)
skythonicO = lambda: do(f3,f4)
skythonic = skythonicD if download_py else skythonicO
skythonic()
ls = lambda: os.system('ls') # TODO: better check if it worked.
print('Installation hopefully worked!')
