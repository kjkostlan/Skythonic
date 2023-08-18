# Tools for keeping track of virtual machines, such as the login keys
import sys, os, time, paramiko
import covert, proj
from waterworks import eye_term, file_io, colorful, plumber
import waterworks.plumber_tools as ptools

proj.platform_import_modules(sys.modules[__name__], ['cloud_vm'])

def our_vm_id():
    return cloud_vm.our_vm_id()

cloud_entry = {'Cloud provider not found automatically, input cloud provider:':proj.which_cloud()}

###############################SSH and SCP######################################

def ssh_bash(instance_id, join_arguments=True):
    # Get the ssh cmd to use the key to enter instance_id.
    # Will get a warning: The authenticity can't be established; this warning is normal and is safe to yes if it is a VM you create in your account.
    # https://stackoverflow.com/questions/65726435/the-authenticity-of-host-cant-be-established-when-i-connect-to-the-instance
    # Python or os.system?
    # https://stackoverflow.com/questions/3586106/perform-commands-over-ssh-with-python
    public_ip = cloud_vm.get_ip(instance_id)
    out = ['ssh', '-i', covert.get_key(instance_id)[1], 'ubuntu@'+str(public_ip)]
    if join_arguments:
        out[2] = '"'+out[2]+'"'
        return ' '.join(out)
    else:
        return out

def ssh_proc_args(instance_id):
    # Splat into into MessyPipe.
    username = 'ubuntu'; hostname = cloud_vm.get_ip(instance_id) #username@hostname
    key_filename = covert.get_key(instance_id)[1]
    return{'username':username,'hostname':hostname, 'key_filename':key_filename}

def patient_ssh_pipe(instance_id, printouts=True, binary_mode=False):
    cloud_vm.start_vm(instance_id)

    pargs = ssh_proc_args(instance_id)
    tubo = eye_term.MessyPipe(proc_type='ssh', proc_args=pargs, printouts=printouts, binary_mode=binary_mode)
    tubo.machine_id = instance_id
    tubo.restart_fn = lambda: cloud_vm.restart_vm(instance_id)

    p = plumber.Plumber(tubo, [], {}, dt=0.5)
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
        colorful.bprint('\nWe closed the SSH\n')
    return _out, _err, tubo

def send_files(instance_id, file2contents, remote_root_folder, printouts=True):
    # None contents are deleted.
    # Both local or non-local paths allowed.
    # Automatically creates folders.
    if printouts:
        colorful.bprint(f'Sending {len(file2contents)} files to {remote_root_folder} {instance_id}')

    tubo = patient_ssh_pipe(instance_id, printouts=printouts)

    p = plumber.Plumber(tubo, [{'commands':[f'mkdir -p {eye_term.quoteless(remote_root_folder)}']}], {}, dt=2.0)
    p.run()

    #https://linuxize.com/post/how-to-use-scp-command-to-securely-transfer-files/
    #scp file.txt username@to_host:/remote/directory/
    public_ip = cloud_vm.get_ip(instance_id)

    tmp_dump = os.path.realpath(proj.dump_folder+'/_vm_tmp_dump')
    file_io.empty_folder(tmp_dump, keeplist=None)

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
    colorful.bprint('WARNING: TODO fix this code to allow deletions and check if the files really were transfered.')
    return tubo

def download_remote_file(instance_id, remote_path, local_dest_folder=None, printouts=True, bin_mode=False):
    # Downalods to a local path or simply returns the file contents.
    save_here = os.path.realpath(proj.dump_folder+'/_vm_tmp_dump/') if local_dest_folder is None else local_dest_folder
    file_io.power_delete(save_here)
    file_io.make_folder(save_here)

    public_ip = cloud_vm.get_ip(instance_id); pem_fname = covert.get_key(instance_id)[1]
    tubo = eye_term.MessyPipe('shell', None, printouts=printouts)
    #https://unix.stackexchange.com/questions/188285/how-to-copy-a-file-from-a-remote-server-to-a-local-machine
    scp_cmd = f'scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -r -i {eye_term.quoteless(pem_fname)} ubuntu@{public_ip}:{eye_term.quoteless(remote_path)} {eye_term.quoteless(save_here)}'

    p = plumber.Plumber(tubo, [{'commands':[scp_cmd+'\necho download_cmd_ran']}], dt=2.0)
    p.run()

    if local_dest_folder is None:
        file_io.power_delete(save_here)

    return out, p.tubo

def update_vms_skythonic(diff): # Where is Skythonic installed?
    colorful.bprint('Warning: TODO: implement propagation of Skythonic updates to other Skythonic-bearing vms.')

########################Installation of packages################################

def _to_pipe(inst_or_pipe, printouts=True): # Idempotent.
    if type(inst_or_pipe) is eye_term.MessyPipe:
        if inst_or_pipe.closed:
            out = inst_or_pipe.remake()
        out = inst_or_pipe
        out.printouts = printouts
        return out
    return patient_ssh_pipe(inst_or_pipe, printouts=printouts)

def update_apt(inst_or_pipe, printouts=None):
    # Updating apt with a restart seems to be the most robust option.
    #https://askubuntu.com/questions/521985/apt-get-update-says-e-sub-process-returned-an-error-code
    if inst_or_pipe is None:
        raise Exception('None instance/pipe')
    test_pairs = [['sudo apt-get update\nsudo apt-get upgrade', 'Reading state information... Done']]
    tubo = _to_pipe(inst_or_pipe, printouts=printouts)

    p = plumber.Plumber(tubo, [{'commands':['sudo rm -rf /tmp/*', 'sudo mkdir /tmp'], 'tests':test_pairs}], {}, dt=0.5)
    p.run()

    if type(inst_or_pipe) is eye_term.MessyPipe:
        p.tubo.close()
    return p.tubo

def upgrade_os(inst_or_pipe, printouts=None):
    # Upgrades the Ubuntu version.
    raise Exception('TODO: Upgrading the OS over SSH seems to not work properly. Instead try to use a newer image in the initial vm.')
    tubo = _to_pipe(inst_or_pipe, printouts=printouts)
    response_map = {**plumber.default_prompts(), **cloud_entry}

    p = plumber.Plumber(tubo, [{'commands':['sudo do-release-upgrade', 'echo hopefully_upgraded_now']}], response_map, dt=2.0)
    tubo = p.run()

    if type(inst_or_pipe) is not eye_term.MessyPipe:
        p.tubo.close()
    return tubo


def _package_info(**kwargs):
    renames = {'apt ping':'apt iputils-ping','apt apache':'apt apache2',
               'apt python':'apt python3-pip', 'apt python3':'apt python3-pip',
               'apt aws':'apt awscli', 'apt netcat':'apt netcat-openbsd'}
    slowness = {'apt awscli':2, 'apt python3-pip':2} # Longer timeouts here.
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

    boto3_err = "AttributeError: module 'lib' has no attribute 'X509_V_FLAG_CB_ISSUER_CHECK'"
    boto3_fix = 'sudo apt upgrade openssl\npip3 install --upgrade boto3 botocore'
    publicAWS_key = 'NO AWS PACKAGE'
    privateAWS_key = 'NO AWS PACKAGE'
    AWSregion_name = 'NO AWS REGION'
    boto3_err = "AttributeError: module 'lib' has no attribute 'X509_V_FLAG_CB_ISSUER_CHECK'"
    boto3_fix = 'sudo apt upgrade openssl\npip3 install --upgrade boto3 botocore'
    if proj.which_cloud()=='aws':
        AWSregion_name = cloud_vm.get_region_name()
        AWSuser_id = covert.user_dangerkey(kwargs['user_name'])
        publicAWS_key, privateAWS_key = covert.get_key(AWSuser_id)
    extra_prompts = {}
    extra_prompts['pip3 boto3'] = {boto3_err:boto3_fix}
    extra_prompts['apt awscli'] = {'Access Key ID':publicAWS_key, 'Secret Access Key':privateAWS_key,
                                   'region name':AWSregion_name, 'output format':'json',
                                   'Geographic area':11, #11 = SystemV
                                   boto3_err:boto3_fix,
                                   'Get:42':'', 'Unpacking awscli':'', # The null prompts (empty string) may help to keep ssh alive
                                   'Setting up fontconfig':'', 'Extracting templates from packages':'',
                                   'Unpacking libaom3:amd64':''}

    toverrides = {}
    make_pip_test = lambda _lib:[f'python3\nimport sys\nimport {_lib}\nx=456*789 if "{_lib}" in sys.modules else 123*456\nprint(x)\nquit()', str(456*789)] # TODO: duplicate code with tmp_plumb.
    toverrides['pip3 azure-core'] = [make_pip_test('azure')]
    fulloverrides = {}
    #https://github.com/Azure/azure-cli/issues/23915
    fulloverrides['azure-cli'] = {'commands':['curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash'], 'tests':[['az', 'Manage Internet of Things (IoT) assets.']]}
    for k in ['apt azure-cli', 'azurecli', 'apt azurecli']:
        fulloverrides[k] = fulloverrides['azure-cli']
    return {'slowness':slowness, 'extra_prompts':extra_prompts, 'extra_cmds':xtra_cmds, 'renames':renames, 'test_overrides':toverrides, 'total_overrides':fulloverrides}

#curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
def install_packages(inst_or_pipe, package_names, extra_tests=None, printouts=None, **kwargs):
    # Includes configuration for common packages;
    # package_name = "apt apache2" or "pip boto3".
    # Some pacakges will require kwards for configuration.
    # Include tests so that the Plumber can ensure that the packages installed properly.
    if not kwargs.get('user_name', None) and proj.which_cloud()=='aws':
        raise Exception('For AWS, must specify a user_name="myUserName" in the **kwargs.')
    details = _package_info(**kwargs)
    if type(package_names) is str:
        package_names = [package_names]

    if inst_or_pipe is None:
        raise Exception('None instance/pipe')
    if extra_tests is None:
        extra_tests = [] # The basic "get-ready for cloud" packages come with thier own tests.
    package_names = [x.lower().replace('_','-').strip() for x in package_names]
    package_names = ['pip3 '+x[3:].strip() if x.startswith('pip ') else x for x in package_names]
    package_names = [details['renames'].get(x, x) for x in package_names]

    for package_name in package_names:
        if package_name=='apt awscli': # This one requires using boto3 so is buried in this conditional.
            colorful.bprint('awscli is a HEAVY installation. Should take about 5 min.')

    tasks = []
    timeout = 64 # TODO: Do we even use this?
    for package_name in package_names:
        timeout = max(timeout, 64*details['slowness'].get(package_name, 1))

    response_map = {**plumber.default_prompts(), **cloud_entry}
    for package_name in package_names:
        response_map = {**response_map, **details['extra_prompts'].get(package_name, {})}

    # Apt response maps:
    response_map['Unable to acquire the dpkg frontend lock'] = 'ps aux | grep -i apt --color=never'
    response_map["you must manually run 'sudo dpkg --configure -a'"] = 'sudo dpkg --configure -a'
    response_map['Unable to locate package'] = 'sudo apt update\nsudo apt upgrade'
    response_map['has no installation candidate'] = 'sudo apt update\nsudo apt upgrade'
    response_map['Some packages could not be installed. This may mean that you have requested an impossible situation'] = 'sudo apt update\nsudo apt upgrade'

    # Pip response maps:
    response_map["Command 'pip' not found"] = 'sudo apt install python3-pip'
    response_map['pip: command not found'] = 'sudo apt install python3-pip'
    response_map['No matching distribution found for'] = 'package not found'
    response_map['Upgrade to the latest pip and try again'] = 'pip3 install --upgrade pip'

    tubo = _to_pipe(inst_or_pipe, printouts=printouts)
    plumber.Plumber(tubo, tasks, response_map, fn_override=None, dt=2.0)

    ## Tasks:
    tasks = []
    for pkg in package_names:
        if details['total_overrides'].get(pkg):
            x = details['total_overrides'].get(pkg)
        else:
            x = {'packages':[pkg], 'commands':details['extra_cmds'].get(pkg,[])}
            if details['test_overrides'].get(pkg):
                x['tests'] = details['test_overrides'].get(pkg)
        tasks.append(x)
    if len(extra_tests)>0: # Better practice is to use tests when there is only one package to install.
        tasks[-1]['tests'] = tasks[-1].get('tests', [])+extra_tests

    p = plumber.Plumber(tubo, tasks, response_map, fn_override=None, dt=2.0)
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

def install_custom_package(inst_or_pipe, package_name, printouts=None, user_name=None):
    # Install packages which we created.
    tubo = _to_pipe(inst_or_pipe, printouts=printouts)
    package_name = package_name.lower().replace('_','-')
    file2contents = {}
    response_map = {}
    dest_folder = ''
    test_pairs = []
    extra_prompts = {}
    cmd_list = []
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

    response_map = {**cloud_entry, **response_map}

    tubo = install_packages(tubo, non_custom_packages, extra_tests=None, printouts=None, user_name=user_name)

    p = plumber.Plumber(tubo, [{'commands':cmd_list, 'tests':test_pairs}], response_map, dt=2.0)
    p.run()

    return p.tubo
