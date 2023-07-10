# Sample proj.py file which should go into the top level of the project folder (and remove this comment).

try:
    dump_folder
except:
    dump_folder = './softwaredump' # Software-generated files go here.

def _install_gitpacks():
    # It may be only one package, but 'waterworks' is essential when working with SSH pipes and the like.
    packs = {}
    packs['./waterworks'] = 'https://github.com/kjkostlan/waterworks'

    for k, v in packs.items():
        k = k.replace('\\','/')
        if k == '.' or k[0:2] != './':
            raise Exception('Forgot the ./<folder>')
        code_in_a_box.download(v, k, clear_folder=False)

def which_cloud(): # Like sys.platform but different mega-cooperations rather than differnt kernels.
    try:
        import boto3
        return 'aws'
    except:
        pass
    TODO

def platform_import_modules(into_this_module, strings):
    # Different for different cloud platforms.
    # The first argument should be "sys.modules[__name__]".
    import importlib
    wc = which_cloud().lower()
    x = None
    if wc == 'aws':
        x = {'cloud_core':'AWS.AWS_core', 'cloud_query':'AWS.AWS_query',\
             'cloud_format':'AWS.AWS_format', 'cloud_clean':'AWS.AWS_clean',\
             'cloud_vm':'AWS.AWS_vm', 'cloud_permiss':'AWS.AWS_permiss'}
    # TODO: other platforms go here.
    for s in strings:
        setattr(into_this_module, s, importlib.import_module(x[s]))

########################## Boilerplate code below ##############################
########### (some of our pacakges depend on global_get and proj.dump_folder) ##########
def global_get(name, initial_value):
    # Proj, by our convention, also handles is where global variables are stored.
    # Any packages that use Proj should use some sort of qualifier to avoid dict key-collisions.
    # This fn is a get function which sets an initial_value if need be.
    if name not in dataset:
        dataset[name] = initial_value
    return dataset[name]

import os
try:
    x
except:
    x = 'The below code should only run once!'
    dataset = {} # Store per-session variables here.

    leaf = '/code_in_a_box.py'
    if not os.path.exists('./'+leaf):
        url = f'https://raw.githubusercontent.com/kjkostlan/Code-in-a-Box/main{leaf}'
        os.system(f'curl "{url}" -o "{"./"+leaf}"')
    import code_in_a_box

    _install_gitpacks()
    #os.unlink('./'+leaf) # Optional delete step.
