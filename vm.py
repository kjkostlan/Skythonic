# Tools for keeping track of virtual machines, such as the login keys.
# See: https://stackoverflow.com/questions/51026026/how-to-pass-private-key-as-text-to-ssh
# Don't forget the chmod 600 on the keys!
# And the fun of scp: https://www.simplified.guide/ssh/copy-file
import pickle, os
import file_io
import AWS.AWS_core as AWS_core

pickle_fname = './softwareDump/vm_info.pypickle'

def _pickleload():
    if os.path.exists(pickle_fname) and os.path.getsize(pickle_fname) > 0:
        with open(pickle_fname,'rb') as f:
            return pickle.load(f)
    return {'instance_id2key_name':{}, 'instance_id2key_material':{}}
def _picklesave(x):
    if not os.path.exists('./softwareDump/'):
        os.makedirs('./softwareDump/')
    with open(pickle_fname,'wb') as f:
        return pickle.dump(x, f)

def update_vms_skythonic(diff):
    # Updates all skythonic files on VMs.
    # Diff can be a partial or full update.
    print('Warning: TODO: implement VM updates.')

def _save_ky1(fname, key_material):
    file_io.fsave(fname, key_material)
    os.chmod(fname, 0o600) # Octal (not hex and not a string!)

def danger_key(instance_id, ky_name, key_material):
    # Saves the private key's material unencrypted. Be careful out there!
    x = _pickleload()
    x['instance_id2key_material'][instance_id] = key_material
    x['instance_id2key_name'][instance_id] = ky_name
    _picklesave(x)
    fname = './softwareDump/'+ky_name+'.pem'
    _save_ky1(fname, key_material)
    return fname

def ssh_cmd(instance_id, address, join=False):
    # Get the ssh cmd to use the key to enter instance_id.
    # Will get a warning: The authenticity can't be established; this warning is normal and is safe to yes if it is a VM you create in your account.
    # https://stackoverflow.com/questions/65726435/the-authenticity-of-host-cant-be-established-when-i-connect-to-the-instance
    # Python or os.system?
    # https://stackoverflow.com/questions/3586106/perform-commands-over-ssh-with-python

    public_ip = AWS_core.id2obj(address)['PublicIp']
    x = _pickleload()
    #cmd = 'ssh -i jumpbox_privatekey.pem ubuntu@'+str(addr['PublicIp'])
    ky_name = x['instance_id2key_name'][instance_id]
    out = ['ssh', '-i', './softwareDump/'+ky_name+'.pem', 'ubuntu@'+str(public_ip)]
    if join:
        out[2] = '"'+out[2]+'"'
        return ' '.join(out)
    else:
        return out
