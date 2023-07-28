# Handles machine and user keys, which are saved in a dump folder.
# TODO: option to encrypt with a password.
# TODO: remove circular covert <-> vm dependencies.
import sys, os, pickle, shutil
import vm, proj
from waterworks import file_io

proj.platform_import_modules(sys.modules[__name__], ['cloud_core', 'cloud_format', 'cloud_permiss'])
platform = proj.which_cloud().lower().strip()

pickle_leaf = 'vm_secrets.pypickle'
pickle_fname = f'{proj.dump_folder}/{pickle_leaf}'

def _fillkeys(x):
    kys = ['instance_id2key_name', 'key_name2key_material', 'username2key']
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
    if not os.path.exists(proj.dump_folder):
        os.makedirs(proj.dump_folder)
    with open(pickle_fname,'wb') as f:
        return pickle.dump(x, f)

def remove_pickle(): # Removes all files. Only use on nuclear cleaning.
    #TODO: remove the pickle.
    _picklesave({})

def _pem(key_name):
    return proj.dump_folder+'/'+key_name+'.pem'

#### Dangerkey functions are create_once functions that return the public and private key ####

def _save_ky1(fname, key_material):
    file_io.fsave(fname, key_material)
    # See: https://stackoverflow.com/questions/51026026/how-to-pass-private-key-as-text-to-ssh
    # Don't forget the chmod 600 on the keys!
    os.chmod(fname, 0o600) # Octal (not hex and not a string!)

def create_vm_dangerkey(vm_name, vm_params, key_name):
    # Creates a new vm with key_name, making a new key and saving the secrets if key_name does not exist.
    # The login name to the vm is 'ubuntu'.
    x = _pickleload()
    fname = _pem(key_name)

    new_key_mat = None
    if key_name not in x['key_name2key_material']: # Must create a new key.
        # Is this platform specific code better moved into the cooresponding folders?
        if platform == 'aws':
            try: # Cant use create_once because of the ephemeral key_material.
                key_pair = cloud_core.create('keypair', key_name, raw_object=True) # Don't use create once b/c we need to know if the user already exists.
                new_key_mat = key_pair.key_material
                if type(new_key_mat) is bytes:
                    new_key_mat = new_key_mat.decode()
            except Exception as e:
                if 'The keypair already exists' in str(e)+repr(e):
                    raise Exception('The keypair exists, but the secret private key cannot be found. If it was lost the VM will be bricked.')
                else:
                    raise e
        elif platform=='azure':
            #from Crypto.PublicKey import RSA
            #the_key = RSA.generate(2048)
            #new_key_mat = the_key.export_key("PEM")
            import cryptography.hazmat.backends as backends
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            private_key = rsa.generate_private_key(public_exponent=65537,key_size=2048,backend=backends.default_backend())
            new_key_mat = private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption())
            new_key_mat = new_key_mat.decode()
        else:
            raise Exception('TODO: covery.py support of platform: '+platform)

    if new_key_mat:
        if type(new_key_mat) is not str:
            raise Exception('New key material must be a str.')
        x['key_name2key_material'][key_name] = new_key_mat
        _save_ky1(fname, new_key_mat)
        print('PEM Key saved to:', fname)
    else:
        print('Reusing this key that was already made:', key_name)
    _picklesave(x)

    if platform=='aws':
        vm_params['KeyName'] = key_name
    elif platform == 'azure':
        #from Crypto.PublicKey import RSA
        #the_key = RSA.import_key(x['key_name2key_material'][key_name])
        #public_key = the_key.publickey().export_key("OpenSSH").decode()
        from azure.mgmt.compute.models import OSProfile
        from cryptography.hazmat.primitives import serialization
        import cryptography.hazmat.backends as backends

        key_mat = x['key_name2key_material'][key_name].encode()
        private_key = serialization.load_pem_private_key(key_mat, backend=backends.default_backend(), password=None) # WARNING: We don't password-protect the keys here.
        public_key = private_key.public_key()
        public_bytes = public_key.public_bytes(encoding=serialization.Encoding.OpenSSH, format=serialization.PublicFormat.OpenSSH)

        lx_conf = {"ssh": {"public_keys": [{"path": "/home/{}/.ssh/authorized_keys".format('ubuntu'), "key_data": public_bytes.decode()}]}}
        vm_params['os_profile'] = OSProfile(computer_name=vm_name, admin_username='ubuntu', linux_configuration=lx_conf)
    else:
        raise Exception('TODO: covery.py support of platform: '+platform)

    inst_id = cloud_core.create_once('machine', vm_name, True, **vm_params)
    x['instance_id2key_name'][inst_id] = key_name
    _picklesave(x)

    return inst_id

def user_dangerkey(user_name):
    # WARNING: makes an ADMIN user.
    user = cloud_core.create_once('user', user_name, True)
    cloud_permiss.attach_user_policy_once(user_name=user_name, policy_id=cloud_permiss.admin_policy_id())

    kpair = cloud_permiss.create_dangerkey_once(user_name)
    if kpair:
        x = _pickleload()
        x['username2key'][user_name] = kpair # Should be a length-2 list.
        _picklesave(x)
        print('Created and saved user key for:', user_name)

    return cloud_format.obj2id(user)

def get_key(id_or_desc):
    # Returns the public and private key. The public key is None if not needed.
    try: # Also allow passing in a user name.
        y = cloud_permiss.keys_user_has(UserName=id_or_desc); x = x[0]
    except Exception as e:
        y = None
    if y:
        return get_key(y)
    the_id = cloud_format.obj2id(id_or_desc)
    x = _pickleload() # At very large scales this query can be some sort of SQL, etc.
    if cloud_format.enumr(the_id) == 'machine':
        key_name = x['instance_id2key_name'].get(the_id,None)
        if key_name is None:
            raise Exception(f'No saved vm key found for {the_id}')
        fname = _pem(key_name)
        return None, os.path.realpath(fname)
    elif cloud_format.enumr(the_id) == 'user':
        desc = cloud_format.id2obj(the_id); uname = desc['UserName']
        if uname not in x['username2key'] and len(cloud_permiss.keys_user_has(user_name=uname))>0:
            raise Exception(f'The keys exist for {uname} but they are not in this keychain and are likely lost. This may mean that the vm is bricked.')
        key_name = x['username2key'].get(uname, None)
        if key_name is None:
            raise Exception(f'No saved user key found for {uname}')
        return key_name
    else:
        raise Exception('No key associated with this kind of resource id: '+the_id)

def danger_copy_keys_to_vm(id_or_desc, skythonic_root_folder, pickle_fname=pickle_fname, printouts=True, preserve_dest=True):
    # Copies the keys and the Pickle.
    dest_folder = skythonic_root_folder+'/'+proj.dump_folder
    the_id = cloud_format.obj2id(id_or_desc)
    x = _pickleload()
    file2contents = {}
    for v in x['instance_id2key_name'].values():
        fname = _pem(v)
        file2contents[fname.replace(proj.dump_folder,'')] = file_io.fload(fname)
    if printouts:
        print(f'Copying secrets to {id}; list is {file2contents.keys()}; vm dest is {dest_folder}')
    vm.send_files(the_id, file2contents, dest_folder, printouts=printouts)

    # Add to any keys held remotely is held remotely:
    tmp_local_folder = proj.dump_folder+'/_covert_tmp/'
    file_io.make_folder(tmp_local_folder)

    tmp_pkl_file = tmp_local_folder+'/'+pickle_leaf
    if preserve_dest:
        vm.download_remote_file(the_id, tmp_local_folder, printouts=printouts)
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
    vm.send_files(the_id, {pickle_leaf:file_io.fload(tmp_pkl_file, bin_mode=True)}, dest_folder, printouts=printouts)
    file_io.power_delete(tmp_local_folder) #Security: delete the file in case of sensitive information on it.
