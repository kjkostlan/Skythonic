# Tools for keeping track of virtual machines, such as the login keys.
# See: https://stackoverflow.com/questions/51026026/how-to-pass-private-key-as-text-to-ssh
# Don't forget the chmod 600 on the keys!
# And the fun of scp: https://www.simplified.guide/ssh/copy-file
import pickle, os
import paramiko
import file_io
import AWS.AWS_format as AWS_format
import eye_term

def get_ip(x): # Address or machine.
    if type(x) is str and '.' in x: # Actually an ip address.
        return x
    if type(x) is str:
        x = AWS_format.id2obj(x)
    if 'PublicIp' in x:
        return x['PublicIp']
    if 'PublicIpAddress' in x:
        return x['PublicIpAddress']
    raise Exception('Cannot find the ip for:'+AWS_format.obj2id(x))

def update_vms_skythonic(diff):
    # Updates all skythonic files on VMs.
    # Diff can be a partial or full update.
    print('Warning: TODO: implement VM updates.')

###############################Command line#####################################

def ssh_cmd(instance_id, join=False):
    # Get the ssh cmd to use the key to enter instance_id.
    # Will get a warning: The authenticity can't be established; this warning is normal and is safe to yes if it is a VM you create in your account.
    # https://stackoverflow.com/questions/65726435/the-authenticity-of-host-cant-be-established-when-i-connect-to-the-instance
    # Python or os.system?
    # https://stackoverflow.com/questions/3586106/perform-commands-over-ssh-with-python
    instance_id = AWS_format.obj2id(instance_id)
    public_ip = get_ip(instance_id)
    out = ['ssh', '-i', key_fname(instance_id), 'ubuntu@'+str(public_ip)]
    if join:
        out[2] = '"'+out[2]+'"'
        return ' '.join(out)
    else:
        return out

def ssh_pipe(instance_id, timeout=8, printouts=True):
    # Returns a MessyPipe which can be interacted with. Don't forget to close() it.
    username = 'ubuntu'; hostname = get_ip(instance_id) #username@hostname

    #https://unix.stackexchange.com/questions/70895/output-of-command-not-in-stderr-nor-stdout?rq=1
    #https://stackoverflow.com/questions/55762006/what-is-the-difference-between-exec-command-and-send-with-invoke-shell-on-para
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # Being permissive is quite a bit easier...
    client.connect(hostname, username=username, key_filename=key_fname(instance_id), timeout=timeout)#password=passphrase)

    return eye_term.MessyPipe(client, printouts)

def ez_ssh_cmds(instance_id, bash_cmds, timeout=8, f_poll=None, printouts=True):
    # This abstraction is quite leaky, so only use when things are simple.
    # f_poll can be a list 1:1 with bash_cmds but this usage is better dealt with paired_ssh_cmds.
    #https://stackoverflow.com/questions/53635843/paramiko-ssh-failing-with-server-not-found-in-known-hosts-when-run-on-we
    #https://stackoverflow.com/questions/59252659/ssh-using-python-via-private-keys
    #https://www.linode.com/docs/guides/use-paramiko-python-to-ssh-into-a-server/
    tubo = ssh_pipe(instance_id, timeout=timeout, printouts=printouts)
    _out, _err = tubo.multi_API(bash_cmds, f_poll=f_poll)
    tubo.close()
    return _out, _err, tubo

def paired_ssh_cmds(instance_id, cmd_pollfn_pairs, timeout=8, printouts=True):
    # Pair each ssh_cmd with the cooresponding expect function.
    return ez_ssh_cmds(instance_id, [x[0] for x in cmd_pollfn_pairs], timeout=timeout, f_poll=[(x+[None])[1] for x in cmd_pollfn_pairs], printouts=printouts)

def send_files(instance_id, file2contents):
    # None contents are deleted.
    print('Sending files to a machine.')
    # Step1: Open ssh client.
    TODO
    # Step2: Send.
