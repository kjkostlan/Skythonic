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
    print('Warning: TODO: implement VM updates.')

def _save_ky1(fname, material):
    file_io.save(fname, key_material)
    os.chmod(fname, '600')

def danger_key(instance_id, ky_name, key_material):
    # Saves the private key's material unencrypted. Be careful out there!
    x = _pickleload()
    x['PEM_private_keys'][instance_id] = key_material
    x['key_names'][instance_id] = ky_name
    _picklesave(x)
    fname = './softwareDump/'+ky_name+'.pem'
    _save_ky1(fname, key_material)
    return fname

def ssh_cmd(instance_id, address, join=False):
    # Get the ssh cmd to use the key to enter instance_id.
    # Will get a warning: The authenticity can't be established; this warning is normal.
    # https://stackoverflow.com/questions/65726435/the-authenticity-of-host-cant-be-established-when-i-connect-to-the-instance
    # Python or os.system?
    # https://stackoverflow.com/questions/3586106/perform-commands-over-ssh-with-python

    public_ip = AWS_core.id2obj(addr)['PublicIp']
    x = _pickleload()
    #cmd = 'ssh -i jumpbox_privatekey.pem ubuntu@'+str(addr['PublicIp'])
    ky_name = x['key_names'][instance_id]
    out = ['ssh', '-i', './softwareDump/'+ky_name+'.pem', 'ubuntu@'+str(public_ip)]
    if join:
        out[2] = '"'+out[2]+'"'
        return out
    else:
        return out
