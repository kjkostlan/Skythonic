import time
import AWS.AWS_query as AWS_query
import AWS.AWS_setup as AWS_setup
import AWS.AWS_format as AWS_format
import AWS.AWS_clean as AWS_clean
import AWS.AWS_core as AWS_core
import vm, covert

class test_results:
    def __init__(self, name=None):
        self.results = []
        self.details = []
        self.names = []
        self.name = name
    def failures(self):
        out = []
        for i in range(len(self.results)):
            if not self.results[i]:
                out.append(self.details[i])
        return out
    def all_passed(self):
        return len(self.failures())==0
    def add_test(self, result, details, name=None):
        self.results.append(result)
        self.details.append(details)
        self.names.append(name)

    def __str__(self):
        fs = self.failures()
        n = len(self.results)
        if len(fs)==0:
            return f'{self.name}: all {n} tests passed!'
        else:
            return f'{self.name}: {len(fs)}/{n} tests failed.'
    def __repr__(self):
        return '<test_results '+str(self)+'>'
    def report(self, verbose=True):
        if self.all_passed():
            return 'No failures to report.'
        lines = []
        for i in range(len(self.results)):
            if not self.results[i]:
                lines.append('FAILED TEST: '+self.names[i]+(': '+str(self.details[i]).replace('\r\n','\n') if verbose else ''))
        return '\n'.join(lines)

def _jump_ssh_cmd_test(results, the_cmd, look_for, vm_id, test_name):
    print('Testing cmd on jumpbox: '+test_name)
    tubo = vm.patient_ssh_pipe(vm_id, printouts=False)

    #tubo.send('echo AWS_test')
    #import time
    #time.sleep(1.0)
    #print('BLitty:', tubo.blit())
    #TODO

    out, err, _ = tubo.API('echo AWS_test')
    tubo.empty(True)
    tubo.send(the_cmd)
    time.sleep(0.25) # Useful if we don't really need laconic_wait.
    vm.laconic_wait(tubo, 'testing', timeout_seconds=24)
    pipe_dump = tubo.blit()
    tubo.close()
    passed = look_for in pipe_dump
    results.add_test(passed, pipe_dump, test_name)

def test_assoc_query():
    # Associations = attachments = connections.
    
    return False

def test_ssh_jumpbox():
    # Tests: A: is everything installed?
    #        B: Are the scp files actually copied over?
    out = test_results('weaker_jumpbox_tests')
    vm_desc = AWS_query.get_by_name('machine', 'BYOC_jumpbox_VM')
    if vm_desc is None:
        raise Exception('Cant find BYOC_jumpbox_VM to test on. Is it named differently or not set up?')

    #tubo = vm.patient_ssh_pipe(vm_desc, printouts=True)
    #tubo.send('cd ~/Skythonic/\npython3\nx=1+2\nprint(x)\nquit()')
    #out, err, _ = tubo.API('echo AWS_test')
    #tubo.empty(True)
    #out, err, _ = tubo.API('cd ~/Skythonic/')
    #tubo.send('python3\nx=1+2\nprint(x)\nquit()')
    #tubo.send('python3')
    #time.sleep(1.0); tubo.update()
    #tubo.send('x = 1+2')
    #time.sleep(1.0); tubo.update()
    #tubo.send('print(x)')
    #time.sleep(1.0); tubo.update()
    #tubo.send('quit()')
    #time.sleep(1.0); tubo.update()
    #tubo.close()
    #return False

    _jump_ssh_cmd_test(out, 'ping', 'ping: usage error: Destination address required', vm_desc, 'Test_ping')
    _jump_ssh_cmd_test(out, 'aws ec2 describe-subnets', 'BYOC_jumpbox_subnet', vm_desc, 'Test_AWS_descsubnets')

    _jump_ssh_cmd_test(out, 'cd ~/Skythonic\n ls -a', 'eye_term.py', vm_desc, 'test files skythonic')

    # Delete and re-install Skythonic:
    _jump_ssh_cmd_test(out, 'rm -rf ~/Skythonic \n echo deleted', 'deleted', vm_desc, 'delete and re-download Skythonic')
    #print('<<Re-Installing Skythonic>>')
    vm.install_Skythonic(vm_desc, '~/Skythonic', printouts=False)
    #print('<<DONE Re-Installing Skythonic>>')
    covert.danger_copy_keys_to_vm(vm_desc, '~/Skythonic', printouts=False)

    _jump_ssh_cmd_test(out, 'cd ~/Skythonic/softwareDump\n ls -a', 'BYOC_keypair.pem', vm_desc, 'test softwareDump')

    _jump_ssh_cmd_test(out, 'cd ~/Skythonic/\npython3\nx=1944+2018\nprint(x)\nquit()', str(1944+2018), vm_desc, 'test py shell')

    return out

def test_new_machine_and_jumpbox():
    #Tests: A: Make a machine in the jumpbox and ssh to it.
    #       B: Make a machine OUTSIDE the jumpbox and ssh to it from the jumpbox.
    jump_desc = AWS_query.get_by_name('machine', 'BYOC_jumpbox_VM')
    if jump_desc is None:
        raise Exception('Cant find BYOC_jumpbox_VM to test on. Is it named differently or not set up?')

    out = test_results('stronger_jumpbox_tests')
    vm.install_Skythonic(jump_desc, '~/Skythonic', printouts=False)

    # First just test non-jumpbox vm:
    vm_name = 'testing_vm'
    subnet_id = AWS_format.obj2id(AWS_query.get_by_name('subnet','BYOC'+'_'+'jumpbox'+'_subnet'))
    if subnet_id is None:
        raise Exception('Cannot find subnet')
    securitygroup_id = AWS_format.obj2id(AWS_query.get_by_name('sgroup','BYOC'+'_'+'jumpbox'+'_sGroup'))
    if securitygroup_id is None:
        raise Exception('Cannot find sgroup')
    private_ip = '10.100.250.111' # Must be in the subnet cidr.
    key_name = 'testing_vm_key_name'
    inst_id = AWS_query.get_by_name('machine', vm_name)
    if AWS_query.lingers(inst_id):
        print(f'Instance {inst_id} was deleted but is lingering and so a new instance with the same name will be created.')
        inst_id = None
    if inst_id is None:
        inst_id = AWS_format.obj2id(AWS_setup.simple_vm(vm_name, private_ip, subnet_id, securitygroup_id, key_name))
        addr = AWS_core.create_once('address', 'testing_address', True, Domain='vpc')
        AWS_setup.wait_and_attach_address(inst_id, addr)
    else:
        print('inst Tags:', AWS_format.tag_dict(inst_id))
        addr = AWS_query.get_by_name('address', 'testing_address')
    try:
        tubo = vm.patient_ssh_pipe(inst_id, printouts=False)
    except Exception as e:
        if 'has been terminated' in str(e):
            AWS_core.delete(inst_id)
            raise Exception('Zombie machine has been deleted. Try running this again')
        else:
            raise e

    AWS_core.delete(inst_id)
    AWS_clean.dep_check_delete(addr, xdeps=None)
    #AWS_core.delete(addr)

    #Test A: Make a machine in the jumpbox and ssh to it.
