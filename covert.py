# Handles machine and user keys, which are saved in a dump folder.
# TODO: option to encrypt with a password.
# TODO: remove circular covert <-> vm dependencies.
import os, pickle, shutil
import boto3
from AWS import AWS_core, AWS_format
import file_io, vm

iam = boto3.client('iam')
pickle_leaf = 'vm_secrets.pypickle'
pickle_fname = f'{file_io.dump_folder}/{pickle_leaf}'

def _fillkeys(x):
    kys = ['instance_id2key_name', 'key_name2key_material', 'username2AWS_key']
    for k in kys:
        if k not in x:
            x[k] = {}
    return x

def _pickleload(pickle_fname=pickle_fname):
    if os.path.exists(pickle_fname) and os.path.getsize(pickle_fname) > 0:
        with open(pickle_fname,'rb') as f:
            return _fillkeys(pickle.load(f))
    return _fillkeys({})
def _picklesave(x, pickle_fname=pickle_fname):
    if not os.path.exists(file_io.dump_folder):
        os.makedirs(file_io.dump_folder)
    with open(pickle_fname,'wb') as f:
        return pickle.dump(x, f)

def remove_pickle(): # Removes all files. Only use on nuclear cleaning.
    #TODO: remove the pickle.
    _picklesave({})

def _pem(key_name):
    return file_io.dump_folder+'/'+key_name+'.pem'

#### Dangerkey functions are create_once functions that return the public and private key ####

def _save_ky1(fname, key_material):
    file_io.fsave(fname, key_material)
    os.chmod(fname, 0o600) # Octal (not hex and not a string!)

def vm_dangerkey(vm_name, vm_params):
    key_name = vm_params['KeyName']
    x = _pickleload()
    key_mat = None
    fname = _pem(key_name)
    try: # Cant use create_once because of the ephemeral key_material.
        key_pair = AWS_core.create('keypair', key_name, raw_object=True) # Don't use create once b/c we need to know if the user already exists.
        key_mat = key_pair.key_material
        x['key_name2key_material'][key_name] = key_mat
        _save_ky1(fname, key_mat)
        print('PEM Key saved to:', fname)
    except Exception as e:
        if 'The keypair already exists' not in str(e)+repr(e): # Key already exists = skip all these steps.
            raise e

        # Key already exists, but make sure the file exists:
        if key_name not in x['key_name2key_material']:
            ec2c = boto3.client('ec2')
            pair = ec2c.describe_key_pairs(Filters=[{'Name': 'key-name', 'Values': [key_name]}])['KeyPairs'][0]
            #for _ in range(16):
            #    print('Tags of the key pair:', AWS_format.tag_dict(pair))
            raise Exception(f'The key-pair {key_name} already exists but the secret is not stored on this machine ({vm.our_vm_id()}).')

    inst_id = AWS_core.create_once('machine', vm_name, True, **vm_params)
    x['instance_id2key_name'][inst_id] = key_name
    _picklesave(x)
    return inst_id

def user_dangerkey(user_name):
    # WARNING: makes an ADMIN user.
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
        key_name = x['instance_id2key_name'].get(id,None)
        if key_name is None:
            raise Exception(f'No saved vm key found for {id}')
        fname = _pem(key_name)
        return None, os.path.realpath(fname)
    elif id.startswith('AID'):
        desc = AWS_format.id2obj(id); uname = desc['UserName']
        if uname not in x['username2AWS_key'] and len(iam.list_access_keys(UserName=uname)['AccessKeyMetadata'])>0:
            raise Exception(f'The keys exist for {uname} but they are not in this keychain and are likely lost. This may mean that the vm is bricked.')
        key_name = x['username2AWS_key'].get(uname, None)
        if key_name is None:
            raise Exception(f'No saved user key found for {uname}')
        return key_name
    else:
        raise Exception('No key associated with this kind of resource id: '+id)

def danger_copy_keys_to_vm(id_or_desc, skythonic_root_folder, pickle_fname=pickle_fname, printouts=True, preserve_dest=True):
    # Copies the keys and the Pickle.
    dest_folder = skythonic_root_folder+'/'+file_io.dump_folder
    id = AWS_format.obj2id(id_or_desc)
    x = _pickleload()
    file2contents = {}
    for v in x['instance_id2key_name'].values():
        fname = _pem(v)
        file2contents[fname.replace(file_io.dump_folder,'')] = file_io.fload(fname)
    if printouts:
        print(f'Copying secrets to {id}; list is {file2contents.keys()}; vm dest is {dest_folder}')
    vm.send_files(id, file2contents, dest_folder, printouts=printouts)

    # Add to any keys held remotely is held remotely:
    tmp_local_folder = file_io.dump_folder+'/_covert_tmp/'
    file_io.make_folder(tmp_local_folder)

    tmp_pkl_file = tmp_local_folder+'/'+pickle_leaf
    if preserve_dest:
        vm.download_remote_file(id, tmp_local_folder, printouts=printouts)
        if os.path.exists(tmp_pkl_file):
            x_remote = _pickleload(pickle_fname=tmp_pkl_file)
            for k in x_remote.keys():
                x[k] = {**x_remote[k], **x[k]}
            if printouts:
                print('Adding to the remote file.')
            _picklesave(x, pickle_fname=tmp_pkl_file) # Save the combined file.
    else:
        if printouts:
            print('No remote file to add to (or preserve_dest set to false), using the local file only.')
        shutil.copyfile(pickle_fname, tmp_pkl_file)
    vm.send_files(id, {pickle_leaf:file_io.fload(tmp_pkl_file, bin_mode=True)}, dest_folder, printouts=printouts)
    file_io.power_delete(tmp_local_folder) #Security: delete the file in case of sensitive information on it.
