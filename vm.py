# Tools for keeping track of virtual machines, such as the login keys.
# See: https://stackoverflow.com/questions/51026026/how-to-pass-private-key-as-text-to-ssh
# Don't forget the chmod 600 on the keys!
# And the fun of scp: https://www.simplified.guide/ssh/copy-file
import pickle, os
import file_io

pickle_fname = './softwareDump/vm_info.pypickle'

def _pickleload():
    if os.path.exists(pickle_fname):
        return pickle.load(pickle_fname)
    return {'PEM_private_keys':{}}
def _picklesave(x):
    return pickle.dump(pickle_fname, x)

def update_vms_skythonic(diff):
    # Updates all skythonic files on VMs.
    # Diff can be a partial or full update.
    print('TODO: implement this feature.')

def _save_ky1(fname, material):
    file_io.save(fname, key_material)
    change_permissionTODO('chmod 600')

def danger_key(instance_id, ky_name, key_material):
    # Saves the private key's material unencrypted. Be careful out there!
    x = _pickleload()
    x['PEM_private_keys'][instance_id] = key_material
    x['key_names'][instance_id] = ky_name
    _picklesave(x)
    fname = './softwareDump/'+ky_name+'.pem'
    _save_ky1(fname, key_material)
    return fname
