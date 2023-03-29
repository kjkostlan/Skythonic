# Handles machine and user keys, which are saved in softwaredump.
# TODO: option to encrypt with a password.
import os, pickle
import boto3
from AWS import AWS_core, AWS_format
import file_io

iam = boto3.client('iam')
pickle_fname = './softwareDump/vm_info.pypickle'

def _fillkeys(x):
    kys = ['instance_id2key_name', 'key_name2key_material', 'username2AWS_key']
    for k in kys:
        if k not in x:
            x[k] = {}
    return x

def _pickleload():
    if os.path.exists(pickle_fname) and os.path.getsize(pickle_fname) > 0:
        with open(pickle_fname,'rb') as f:
            return _fillkeys(pickle.load(f))
    return _fillkeys({})
def _picklesave(x):
    if not os.path.exists('./softwareDump/'):
        os.makedirs('./softwareDump/')
    with open(pickle_fname,'wb') as f:
        return pickle.dump(x, f)

def remove_pickle(): # Removes all files. Only use on nuclear cleaning.
    #TODO: remove the pickle.
    _picklesave({})

#### Dangerkey functions are create_once functions that return the public and private key ####

def _save_ky1(fname, key_material):
    file_io.fsave(fname, key_material)
    os.chmod(fname, 0o600) # Octal (not hex and not a string!)

def vm_dangerkey(vm_name, vm_params):
    key_name = vm_params['KeyName']
    x = _pickleload()
    key_mat = None
    fname = './softwareDump/'+key_name+'.pem'
    try: # Cant use create_once because of the ephemeral key_material.
        key_pair = AWS_core.create('keypair', key_name, raw_object=True) # Don't use create once b/c we need to know if the user already exists.
        key_mat = key_pair.key_material
        x['key_name2key_material'][key_name] = key_mat
        _save_ky1(fname, key_mat)
        print('PEM Key saved to:', fname)
    except Exception as e:
        if 'The keypair already exists' not in str(e)+repr(e): # Key already exists = skip all these steps.
            raise e

    inst_id = AWS_core.create_once('machine', vm_name, True, **vm_params)
    x['instance_id2key_name'][inst_id] = key_name
    _picklesave(x)
    return inst_id

def user_dangerkey(user_name):
    # WARNING: makes an admin user.
    user = AWS_core.create_once('user', user_name, True)
    try:
        iam.attach_user_policy(UserName=user_name, PolicyArn = 'arn:aws:iam::aws:policy/AdministratorAccess')
    except Exception as e:
        if 'already exists' not in str(e):
            raise e
    kys = iam.list_access_keys(UserName=user_name)['AccessKeyMetadata'] #Note: the user access keys are disjoint from the global access keys.
    if len(kys)==0: # No keys attached to this user.
        key_dict = iam.create_access_key(UserName=user_name)
        k0 = key_dict['AccessKey']['AccessKeyId']
        k1 = key_dict['AccessKey']['SecretAccessKey']
        x = _pickleload()
        x['username2AWS_key'][user_name] = [k0, k1]
        _picklesave(x)
        print('Created and saved user key for:', user_name)

    return AWS_format.obj2id(user)

def get_key(id_or_desc):
    # Returns the public and private key. The public key is None if not needed.
    id = AWS_format.obj2id(id_or_desc)
    try: # Also allow pssing in a user name.
        x = iam.list_access_keys(UserName=id_or_desc)['AccessKeyMetadata']; x = x[0]
        return get_key(x)
    except Exception as e:
        pass
    x = _pickleload() # At very large scales this query can be some sort of SQL, etc.
    if id.startswith('i-'):
        key_name = x['instance_id2key_name'][id]
        fname = './softwareDump/'+key_name+'.pem'
        return None, fname
    elif id.startswith('AID'):
        desc = AWS_format.id2obj(id); uname = desc['UserName']
        if uname not in x['username2AWS_key'] and len(iam.list_access_keys(UserName=uname)['AccessKeyMetadata'])>0:
            raise Exception(f'The keys exist for {uname} but they are not in this keychain and are thus lost. They need to be replaced.')
        return x['username2AWS_key'][uname]
    else:
        raise Exception('No key associated with this kind of resource id: '+id)

'''
def simple_admin_user(uname='BYOA'):
    # Returns the key.
    user = AWS_core.create_once('user', uname, True)
    iam.attach_user_policy(UserName=uname, PolicyArn = 'arn:aws:iam::aws:policy/AdministratorAccess')
    ky = vm.user_key(uname)
    if ky is None:
        print('Creating user key')
        key_dict = iam.create_access_key(UserName=uname)
        k0 = key_dict['AccessKey']['AccessKeyId']
        k1 = key_dict['AccessKey']['SecretAccessKey']
        vm.danger_user_key(uname, k0, k1)
        ky = [k0, k1]
    return ky


#def danger_user_key(user_name, public_key, private_key):
#    x = _pickleload()
#    x['username2AWS_key'][user_name] = [public_key, private_key]
#    _picklesave(x)
#    return True

#def key_fname(instance_id):
#    x = _pickleload(); ky_name = x['instance_id2key_name'][instance_id]
#    return './softwareDump/'+ky_name+'.pem'

#def user_key(user_name):
#    x = _pickleload()
#    return x['username2AWS_key'].get(user_name, None)

#def danger_key(instance_id, ky_name, key_material=None):
    # Stores which instance uses what key.
    # Saves the private key's material unencrypted (if not None). Be careful out there!
#    x = _pickleload()
#    x['instance_id2key_name'][instance_id] = ky_name
#    x['key_name2key_material'][ky_name] = key_material
#    _picklesave(x)
#    fname = './softwareDump/'+ky_name+'.pem'
#    if key_material is not None:
#        _save_ky1(fname, key_material)
#    return fname

'''
