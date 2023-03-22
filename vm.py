# Tools for keeping track of virtual machines, such as the login keys.
# See: https://stackoverflow.com/questions/51026026/how-to-pass-private-key-as-text-to-ssh
# Don't forget the chmod 600 on the keys!
# And the fun of scp: https://www.simplified.guide/ssh/copy-file
import pickle, os
import file_io
import AWS.AWS_format as AWS_format

pickle_fname = './softwareDump/vm_info.pypickle'

def _fillkeys(x):
    kys = ['instance_id2key_name', 'key_name2key_material']
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

def update_vms_skythonic(diff):
    # Updates all skythonic files on VMs.
    # Diff can be a partial or full update.
    print('Warning: TODO: implement VM updates.')

def _save_ky1(fname, key_material):
    file_io.fsave(fname, key_material)
    os.chmod(fname, 0o600) # Octal (not hex and not a string!)

def danger_key(instance_id, ky_name, key_material=None):
    # Stores which instance uses what key.
    # Saves the private key's material unencrypted (if not None). Be careful out there!
    x = _pickleload()
    x['instance_id2key_name'][instance_id] = ky_name
    x['key_name2key_material'][ky_name] = key_material
    _picklesave(x)
    fname = './softwareDump/'+ky_name+'.pem'
    if key_material is not None:
        _save_ky1(fname, key_material)
    return fname

def ssh_cmd(instance_id, address, join=False):
    # Get the ssh cmd to use the key to enter instance_id.
    # Will get a warning: The authenticity can't be established; this warning is normal and is safe to yes if it is a VM you create in your account.
    # https://stackoverflow.com/questions/65726435/the-authenticity-of-host-cant-be-established-when-i-connect-to-the-instance
    # Python or os.system?
    # https://stackoverflow.com/questions/3586106/perform-commands-over-ssh-with-python
    address = AWS_format.id2obj(address)
    public_ip = address.get('PublicIp',None)
    if public_ip is None:
        public_ip = address['PublicIpAddress']
    x = _pickleload()
    ky_name = x['instance_id2key_name'][instance_id]
    out = ['ssh', '-i', './softwareDump/'+ky_name+'.pem', 'ubuntu@'+str(public_ip)]
    if join:
        out[2] = '"'+out[2]+'"'
        return ' '.join(out)
    else:
        return out

## General idea of how to run code on jump boxes:
# Paramiko is built in.
#https://www.linode.com/docs/guides/use-paramiko-python-to-ssh-into-a-server/
def send_cmds(instance_id, bash_cmds, timeout=8):
    # Valid bach cmds:
    #  A string (will be split by newline)
    #  A list/tuple (each entry is one line).
    #  A function of (output, err). Use None to end the ssh fn.
    print('Sending commands to:', instance_id)
    # TODO: Gets the outputs.
    #https://stackoverflow.com/questions/53635843/paramiko-ssh-failing-with-server-not-found-in-known-hosts-when-run-on-we
    #https://stackoverflow.com/questions/59252659/ssh-using-python-via-private-keys
    #https://www.linode.com/docs/guides/use-paramiko-python-to-ssh-into-a-server/
    #https://hackersandslackers.com/automate-ssh-scp-python-paramiko/
    username = 'ubuntu'; hostname = TODO #username@hostname

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # Bieng permissive is quite a bit easier...
    client.connect(hostname, username=username, key_filename=key_filename, timeout=timeout)#password=passphrase)

    outputs = []; errors = []

    if type(bash_cmds) is str:
        bash_cmds = '\n'.split(bash_cmds.strip())
    if not callable(bash_cmds):
        x = bash_cmds+[None]
        bash_cmds = lambda out, err: next(x)

    last_out = None; last_err = None
    outputs = []; errs = []
    while True:
        the_cmd = bash_cmds(last_out, last_err)
        if the_cmd is None or the_cmd is False:
            break
        _stdin, _stdout, _stderr = client.exec_command(the_cmd)
        last_out = _stdout.read().decode()
        last_err = _strerr.read().decode()
        outputs.append(last_out); errs.append(last_err)

    client.close()
    return outputs, errs

def send_files(instance_id, file2contents):
    # None contents are deleted.
    print('Sending files to a machine.')
    # Step1: Open ssh client.
    TODO
    # Step2: Send.
