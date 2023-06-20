# Tools for keeping track of virtual machines, such as the login keys
# See: https://stackoverflow.com/questions/51026026/how-to-pass-private-key-as-text-to-ssh
# Don't forget the chmod 600 on the keys!
# And the fun of scp: https://www.simplified.guide/ssh/copy-file
import paramiko, time, os
import covert
from waterworks import eye_term, plumber, file_io

platform = 'AWS' # Different platforms will be supported here.
if platform == 'AWS':
    import AWS.AWS_vm as CLOUD_vm
else:
    raise Exception(f'Support not yet implemented for {platform}')

def our_vm_id():
    return CLOUD_vm.our_vm_id()

###############################SSH and SCP######################################

def ssh_bash(instance_id, join_arguments=True):
    # Get the ssh cmd to use the key to enter instance_id.
    # Will get a warning: The authenticity can't be established; this warning is normal and is safe to yes if it is a VM you create in your account.
    # https://stackoverflow.com/questions/65726435/the-authenticity-of-host-cant-be-established-when-i-connect-to-the-instance
    # Python or os.system?
    # https://stackoverflow.com/questions/3586106/perform-commands-over-ssh-with-python
    public_ip = CLOUD_vm.get_ip(instance_id)
    out = ['ssh', '-i', covert.get_key(instance_id)[1], 'ubuntu@'+str(public_ip)]
    if join_arguments:
        out[2] = '"'+out[2]+'"'
        return ' '.join(out)
    else:
        return out

def ssh_proc_args(instance_id):
    # Splat into into MessyPipe.
    username = 'ubuntu'; hostname = CLOUD_vm.get_ip(instance_id) #username@hostname
    key_filename = covert.get_key(instance_id)[1]
    return{'username':username,'hostname':hostname, 'key_filename':key_filename}

def patient_ssh_pipe(instance_id, printouts=True, binary_mode=False):
    CLOUD_vm.start_vm(instance_id)

    pargs = ssh_proc_args(instance_id)
    tubo = eye_term.MessyPipe(proc_type='ssh', proc_args=pargs, printouts=printouts, binary_mode=binary_mode)
    tubo.machine_id = instance_id
    tubo.restart_fn = lambda: CLOUD_vm.restart_vm(instance_id)

    p = plumber.Plumber(tubo, [], {}, [], 'default', dt=0.5)
    p.run()
    return p.tubo

def lazy_run_ssh(instance_id, bash_cmds, f_polls=None, printouts=True):
    # This abstraction is quite leaky, so *only use when things are very simple and consistent*.
    # f_poll can be a list 1:1 with bash_cmds but this usage is better dealt with paired_ssh_cmds.
    #https://stackoverflow.com/questions/53635843/paramiko-ssh-failing-with-server-not-found-in-known-hosts-when-run-on-we
    #https://stackoverflow.com/questions/59252659/ssh-using-python-via-private-keys
    #https://www.linode.com/docs/guides/use-paramiko-python-to-ssh-into-a-server/
    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    _out, _err, _ = tubo.multi_API(bash_cmds, f_polls=f_polls)
    tubo.close()
    if tubo.printouts:
        eye_term.bprint('\nWe closed the SSH\n')
    return _out, _err, tubo

def send_files(instance_id, file2contents, remote_root_folder, printouts=True):
    # None contents are deleted.
    # Both local or non-local paths allowed.
    # Automatically creates folders.
    if printouts:
        eye_term.bprint(f'Sending {len(file2contents)} files to {remote_root_folder} {instance_id}')

    tubo = patient_ssh_pipe(instance_id, printouts=printouts)
    p = plumber.Plumber(tubo, [], {}, [f'mkdir -p {eye_term.quoteless(remote_root_folder)}'], [], dt=2.0)
    p.run()

    #https://linuxize.com/post/how-to-use-scp-command-to-securely-transfer-files/
    #scp file.txt username@to_host:/remote/directory/
    public_ip = CLOUD_vm.get_ip(instance_id)

    tmp_dump = os.path.realpath(proj.dump_folder+'/_vm_tmp_dump')
    file_io.empty_folder(tmp_dump, ignore_permiss_error=False, keeplist=None)

    # Enclosing folders that need to be made:
    folders = set()
    for k in file2contents.keys():
        pieces = k.replace('\\','/').split('/')
        for j in range(len(pieces)-1):
            folders.add('/'.join(pieces[0:j]))
    folders = list(folders); folders.sort(key=lambda x:len(x.split('/')))

    # Make, from shortest to longest:
    for k in file2contents.keys():
        file_io.fsave(tmp_dump+'/'+k, file2contents[k])

    pem_fname = covert.get_key(instance_id)[1]
    #https://serverfault.com/questions/330503/scp-without-known-hosts-check
    tmp_dump1 = tmp_dump+'/*'
    scp_cmd = f'scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -r -i {eye_term.quoteless(pem_fname)} {eye_term.quoteless(tmp_dump1)} ubuntu@{public_ip}:{eye_term.quoteless(remote_root_folder)}'

    tubo = eye_term.MessyPipe('shell', None, printouts=printouts)
    tubo.send(scp_cmd)
    tubo.API('echo scp_cmd_sent') # Getting the output from the scp command is ... tricky. Use echos instead:

    file_io.power_delete(tmp_dump)
    eye_term.bprint('WARNING: TODO fix this code to allow deletions and check if the files really were transfered.')
    return tubo

def download_remote_file(instance_id, remote_path, local_dest_folder=None, printouts=True, bin_mode=False):
    # Downalods to a local path or simply returns the file contents.
    save_here = os.path.realpath(proj.dump_folder+'/_vm_tmp_dump/') if local_dest_folder is None else local_dest_folder
    file_io.power_delete(save_here)
    file_io.make_folder(save_here)

    public_ip = CLOUD_vm.get_ip(instance_id); pem_fname = covert.get_key(instance_id)[1]
    tubo = eye_term.MessyPipe('shell', None, printouts=printouts)
    #https://unix.stackexchange.com/questions/188285/how-to-copy-a-file-from-a-remote-server-to-a-local-machine
    scp_cmd = f'scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -r -i {eye_term.quoteless(pem_fname)} ubuntu@{public_ip}:{eye_term.quoteless(remote_path)} {eye_term.quoteless(save_here)}'

    p = plumber.Plumber(tubo, [], {}, [scp_cmd+'\necho download_cmd_ran'], 'default', dt=2.0)
    p.run()

    if local_dest_folder is None:
        file_io.power_delete(save_here)

    return out, p.tubo

def update_vms_skythonic(diff):
    # Updates all skythonic files on VMs.
    eye_term.bprint('Warning: TODO: implement this auto-update Skythonic function.')

########################Installation of packages################################

def _to_pipe(inst_or_pipe, printouts=None): # Idempotent.
    if type(inst_or_pipe) is eye_term.MessyPipe:
        if inst_or_pipe.closed:
            out = inst_or_pipe.remake()
        out = inst_or_pipe
        if printouts is True or printouts is False:
            out.printouts = printouts
        return out
    return patient_ssh_pipe(inst_or_pipe, printouts=not printouts is False)

def update_apt(inst_or_pipe, printouts=None):
    # Updating apt with a restart seems to be the most robust option.
    #https://askubuntu.com/questions/521985/apt-get-update-says-e-sub-process-returned-an-error-code
    if inst_or_pipe is None:
        raise Exception('None instance/pipe')
    pairs = [['sudo apt-get update\nsudo apt-get upgrade', 'Reading state information... Done']]
    tubo = _to_pipe(inst_or_pipe, printouts=printouts)

    p = plumber.Plumber(tubo, [], {}, ['sudo rm -rf /tmp/*', 'sudo mkdir /tmp'], pairs, dt=0.5)
    p.run()

    if type(inst_or_pipe) is eye_term.MessyPipe:
        p.tubo.close()
    return p.tubo

def upgrade_os(inst_or_pipe, printouts=None):
    # Upgrades the Ubuntu version.
    raise Exception('TODO: Upgrading the OS over SSH seems to not work properly. Instead try to use a newer image in the initial vm.')
    tubo = _to_pipe(inst_or_pipe, printouts=printouts)
    response_map = {**plumber.default_prompts(), **{}}
    p = plumber.Plumber(tubo, [], response_map, ['sudo do-release-upgrade', 'echo hopefully_upgraded_now'], [], dt=2.0)
    tubo = p.run()

    if type(inst_or_pipe) is not eye_term.MessyPipe:
        p.tubo.close()
    return tubo

def install_package(inst_or_pipe, package_name, printouts=None, **kwargs):
    # Includes configuration for common packages;
    # package_name = "apt apache2" or "pip boto3".
    # Some pacakges will require kwards for configuration.
    package_name = package_name.lower() # Lowercase, 0-9 -+ only.
    if package_name.startswith('pip '):
        package_name = 'pip3 '+package_name[3:].strip()

    if inst_or_pipe is None:
        raise Exception('None instance/pipe')
    renames = {'apt ping':'apt iputils-ping','apt apache':'apt apache2',
               'apt python':'apt python3-pip', 'apt python3':'apt python3-pip',
               'apt aws':'apt awscli', 'apt netcat':'apt netcat-openbsd'}
    package_name = renames.get(package_name, package_name)

    xtra_cmds = {}
    xtra_cmds['apt apache2'] = ['sudo apt install libcgi-session-perl',
            'sudo systemctl enable apache2',
            'cd /etc/apache2/mods-enabled',
            'sudo ln -s ../mods-available/cgi.load cgi.load',
            'sudo ln -s ../mods-available/ssl.conf ssl.conf',
            'sudo ln -s ../mods-available/ssl.load ssl.load',
            'sudo ln -s ../mods-available/socache_shmcb.load socache_shmcb.load',
            'cd /etc/apache2/sites-enabled',
            'sudo ln -s ../sites-available/default-ssl.conf default-ssl.conf']
    xtra_cmds['apt awscli'] = ['aws configure']
    xtra_cmds['apt python3-pip'] = ['PYTHON3_PATH=$(which python3)', 'sudo ln -sf $PYTHON3_PATH /usr/local/bin/python', 'sudo apt upgrade python3']

    xtra_packages = {}
    xtra_packages['apt awscli'] = ['pip boto3']
    #xtra_packages['apt python3-pip'] = ['apt python-is-python3'] # This package can't always be found for some reason.

    timeouts = {'apt awscli':128, 'apt python3-pip':128}
    timeout = timeouts.get(package_name, 64)

    tests = {}
    tests['apt iputils-ping'] = [['ping -c 1 localhost', '0% packet loss']]
    tests['apt apache2'] = [['sudo service apache2 start',''],
                            ['curl -k http://localhost', ['apache2', '<div>', '<html']],
                            ['systemctl status apache2.service', ['The Apache HTTP Server', 'Main PID:']]]
    tests['apt python3-pip'] = [['python3\nprint(id)\nquit()', '<built-in function id>']]
    tests['apt awscli'] = [['aws ec2 describe-vpcs --output text', 'CIDRBLOCKASSOCIATIONSET'],
                           ["python3\nimport boto3\nboto3.client('ec2').describe_vpcs()\nquit()","'Vpcs': [{'CidrBlock'"]]

    extra_prompts = {}
    boto3_err = "AttributeError: module 'lib' has no attribute 'X509_V_FLAG_CB_ISSUER_CHECK'"
    boto3_fix = 'sudo apt upgrade openssl\npip3 install --upgrade boto3 botocore'
    extra_prompts['pip3 boto3'] = {boto3_err:boto3_fix}

    if package_name=='apt awscli': # This one requires using boto3 so is buried in this conditional.
        eye_term.bprint('awscli is a HEAVY installation. Should take about 5 min.')
        region_name = CLOUD_vm.get_region_name()
        user_id = covert.user_dangerkey(kwargs['user_name'])
        publicAWS_key, privateAWS_key = covert.get_key(user_id)

        # The null prompts (empty string) may help to keep ssh alive:
        extra_prompts['apt awscli'] = {'Access Key ID':publicAWS_key, 'Secret Access Key':privateAWS_key,
                                    'region name':region_name, 'output format':'json',
                                    'Geographic area':11, #11 = SystemV
                                    boto3_err:boto3_fix,
                                    'Get:42':'', 'Unpacking awscli':'',
                                    'Setting up fontconfig':'', 'Extracting templates from packages':'',
                                    'Unpacking libaom3:amd64':''}

    ### Core installation:
    package_name = package_name.lower().replace('_','-')
    package_name = renames.get(package_name, package_name) # Lowercase, 0-9 -+ only.
    package_manager = package_name.split()

    tubo = _to_pipe(inst_or_pipe, printouts=printouts)
    response_map = {**plumber.default_prompts(), **extra_prompts.get(package_name,{})}
    p = plumber.Plumber(tubo, [package_name]+xtra_packages.get(package_name,[]), response_map, xtra_cmds.get(package_name, []), tests.get(package_name, []), dt=2.0)
    tubo = p.run()

    if type(inst_or_pipe) is not eye_term.MessyPipe:
        p.tubo.close()
    return p.tubo

###############Installation of our packages and configs#########################

def update_Skythonic(inst_or_pipe, remote_root_folder='~/Skythonic', printouts=None):
    #Updates skythonic with what is stored locally (on the machine calling this fn).
    # Basically the same as install_custom_package(inst_or_pipe, skythonic) but with no testing.
    tubo = _to_pipe(inst_or_pipe, printouts=printouts)

    file2contents = file_io.folder_load('.', allowed_extensions='.py')
    for k in list(file2contents.keys()):
        if proj.dump_folder.split('/')[-1] in k:
            del file2contents[k]
    tubo = send_files(tubo.machine_id, file2contents, remote_root_folder, printouts=tubo.printouts)

    if type(inst_or_pipe) is not eye_term.MessyPipe:
        tubo.close()
    return tubo

def install_custom_package(inst_or_pipe, package_name, printouts=None):
    # Install packages which we created.
    tubo = _to_pipe(inst_or_pipe, printouts=printouts)
    package_name = package_name.lower().replace('_','-')
    file2contents = {}
    response_map = {}
    dest_folder = ''
    test_pairs = None
    extra_prompts = {}
    cmd_list = None
    timeout = 12
    non_custom_packages = []

    ### Per package information:
    if package_name == 'skythonic': # Local copy.
        file2contents = file_io.folder_load('.', allowed_extensions='.py')
        for k in list(file2contents.keys()):
            if proj.dump_folder.split('/')[-1] in k:
                del file2contents[k]
        dest_folder = '~/Skythonic'
        test_pairs = [['cd Skythonic\npython3\nfrom waterworks import file_io\nprint(file_io)\nquit()','module']]
        non_custom_packages = ['pip paramiko']
    elif package_name=='host-list':
        dest_folder = '/etc'
        cmd_list = [f'cd {dest_folder}', 'sudo wget https://developmentserver.com/BYOC/Resources/hosts.txt', 'sudo mv -f hosts.txt hosts', f"sudo sh -c 'echo jump > {dest_folder}/hostname'"]
    elif package_name=='app-server':
        cmd_list = ['cd /usr/local/bin',
                     'sudo wget https://developmentserver.com/BYOC/Resources/addserver.txt',
                     'sudo wget https://developmentserver.com/BYOC/Resources/addserver.pl.txt',
                     'sudo wget https://developmentserver.com/BYOC/Resources/rmserver.txt',
                     'sudo wget https://developmentserver.com/BYOC/Resources/rmserver.pl.txt',
                     'sudo mv addserver.txt addserver',
                     'sudo mv addserver.pl.txt addserver.pl',
                     'sudo mv rmserver.txt rmserver',
                     'sudo mv rmserver.pl.txt rmserver.pl',
                     'sudo chmod a+x *',
                     "sudo sh -c 'echo app1 > /etc/hostname'"]
    elif package_name=='web-server':
        cmd_list = ['cd /var/www/html', 'sudo wget https://developmentserver.com/BYOC/Resources/CiscoWorldLogo.jpg',
                     'sudo wget https://developmentserver.com/BYOC/Resources/index.html.txt',
                     'sudo mv index.html.tx index.html',
                     'cd /usr/lib/cgi-bin',
                     'sudo wget https://developmentserver.com/BYOC/Resources/index.cgi.txt',
                     'sudo wget https://developmentserver.com/BYOC/Resources/qr1.cgi.txt',
                     'sudo mv index.cgi.txt index.cgi',
                     'sudo mv qr1.cgi.txt qr1.cgi',
                     'sudo chmod a+x *',
                     'sudo a2enmod cgid',
                     "sudo sh -c 'echo web1 >/etc/hostname'",
                     'sudo systemctl restart apache2',
                     'systemctl status apache2.service --no-pager',
                     'sudo apachectl configtest',
                     'journalctl -xeu apache2.service --no-pager']
    else:
        raise Exception(f'Unrecognized custom package {package_name}')

    if len(file2contents)>0:
        send_files(tubo.machine_id, file2contents, dest_folder, printouts=tubo.printouts)

    p = plumber.Plumber(tubo, non_custom_packages, response_map, cmd_list, test_pairs, dt=2.0)
    p.run()

    return p.tubo
