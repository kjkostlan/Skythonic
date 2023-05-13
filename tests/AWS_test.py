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

def _jump_ssh_cmd_test(results, the_cmd, look_for, vm_id, test_name, printouts=True):
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
    if not passed:
        print('Testing cmd on jumpbox failed: '+test_name+' looked for but did not find: '+look_for)

def test_ip_cidr(printouts=True):
    # Such a simple tehcnical test.
    out = True
    gold = ['123.456.7.8', '123.456.7.8/32', '123.456.7.0/24', '123.456.0.0/16', '123.0.0.0/8', '0.0.0.0/0']
    green = AWS_query.enclosing_cidrs('123.456.7.8')
    out = out and gold==green
    if printouts and not gold==green:
        print('Gold vs green:', [gold[i]+' '+green[i] for i in range(len(gold))])
    gold = ['555.444.3.0/24', '555.444.0.0/16', '555.0.0.0/8', '0.0.0.0/0']
    green = AWS_query.enclosing_cidrs('555.444.3.0/24')
    out = out and gold==green
    if printouts and not gold==green:
        print('Gold vs green:', [gold[i]+' '+green[i] for i in range(len(gold))])
    return out

def test_obj2id(printouts=True):
    out = True
    all = AWS_query.get_resources()
    n = 0
    for k in all.keys():
        for x in all[k]:
            the_id =AWS_format.obj2id(x)
            x1 = AWS_format.id2obj(the_id)
            the_id2 = AWS_format.obj2id(x1)
            if printouts:
                if type(x) is not dict:
                    print('Original qurey not a dict:\n', x)
                if type(x1) is not dict and type(x) is dict:
                    print('New query not a dict:\n', x)
                if type(the_id) is not str:
                    print('Converting this to an id failed:\n',x)
                if the_id != the_id2:
                    print('Id round trip not equal:',the_id, the_id2)
                if x != x1:
                    print('Difference in round-trip dict-to-dict; may be a subtle difference not our fault but needs to be OKed by this fn if so.')
            out = out and type(the_id) is str and type(x) is dict and type(x1) is dict and the_id2==the_id and x==x1
            n = n+1
    if n<8:
        raise Exception('Not enough resource to give a good test of this fn.')
    return out

def test_assoc_query(printouts=True):
    # Associations must be symmetric.
    out = True

    # Associations = attachments = connections.
    if printouts:
        print('This test is expensive O(n^2) for large amounts of resources.')
    safe_err_msgs = ['thier own kind', 'directly associated with']
    all = AWS_query.get_resources()
    if printouts:
        print('Total resource counts:', [f'{k}={len(all[k])}' for k in all.keys()])

    AWS_types = ['webgate', 'vpc', 'subnet', 'kpair', 'sgroup', 'rtable', 'machine', 'address','peering','user', 'IAMpolicy']
    has_resources = {}
    resc_count = 0; link_count = 0
    link_map = {} # {id:[resources]}
    err_map = {} #{type_type:error}, only one error at a time. Makes sure reciprocal.
    for ty in AWS_types:
        if printouts:
            print('Working on connections to:', ty)
        for ky in all.keys():
            for x in all[ky]:
                has_resources[ky] = True
                the_id = AWS_format.obj2id(x)
                try:
                    links = AWS_query.assocs(x, ty)
                    if the_id not in link_map:
                        link_map[the_id] = []
                    link_map[the_id].extend(links); link_count = link_count+len(links)
                except Exception as e:
                    bad_err = True
                    for msg in safe_err_msgs:
                        if msg in str(e):
                            _tmp = the_id+ AWS_format.enumr(the_id)+'_'+ty# DEBUG
                            err_map[AWS_format.enumr(the_id)+'_'+ty] = msg
                            bad_err = False
                    if bad_err:
                        raise e
            resc_count += 1
    if printouts:
        print('Done with heavy AWS API usage.')

    if resc_count<10:
        raise Exception('So few resources that this test cannot be trusted.')
    if link_count<12:
        raise Exception('Too few links between resources.')

    # Test reciprocity:
    reverse_link_map = {} #Also {id:[resources]}
    for orig_id in link_map.keys():
        for dest_id in link_map[orig_id]:
            if dest_id not in reverse_link_map:
                reverse_link_map[dest_id] = []
            reverse_link_map[dest_id].append(orig_id)

    forward_only = []; reverse_only = []; total_oneways = 0

    kys = set(list(link_map.keys())+list(reverse_link_map.keys()))
    for ky in kys:
        l0 = set(link_map.get(ky,[])); l1 = set(reverse_link_map.get(ky,[]))
        for hanging in l0-l1:
            forward_only.append(hanging)
        for hanging in l1-l0:
            reverse_only.append(hanging)
        if printouts:
            if len(l0-l1)>0:
                total_oneways = total_oneways+len(l0-l1)
                print('One way forward-only connection:', ky, 'to', l0-l1)
            #if len(l1-l0)>0: # Redundent.
            #    print('One way reverse-only connection:', ky, 'from', l1-l0)
    out = out and len(forward_only)+len(reverse_only)==0
    bad_kys = []
    for k in err_map.keys(): # Errors must also have reciprocity
        pieces = k.split('_')
        if has_resources.get(pieces[0], False) and has_resources.get(pieces[1],False): # Only two-way errors.
            k1 = pieces[1]+'_'+pieces[0]
            if err_map[k] != err_map.get(k1,None):
                out = False
                bad_kys.append(k)
                if printouts:
                    print(f'Forward and reverse errs not the same for {k}; {err_map[k]} vs {err_map.get(k1,None)}')

    return out

def test_ssh_jumpbox(printouts=True):
    # Tests: A: is everything installed?
    #        B: Are the scp files actually copied over?
    # (printotus will not print everything, only test failures)
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

    _jump_ssh_cmd_test(out, 'ping', 'ping: usage error: Destination address required', vm_desc, 'Test_ping', printouts)
    _jump_ssh_cmd_test(out, 'aws ec2 describe-subnets', 'BYOC_jumpbox_subnet', vm_desc, 'Test_AWS_descsubnets', printouts)

    _jump_ssh_cmd_test(out, 'cd ~/Skythonic\n ls -a', 'eye_term.py', vm_desc, 'test files skythonic', printouts)

    # Delete and re-install Skythonic:
    _jump_ssh_cmd_test(out, 'rm -rf ~/Skythonic \n echo deleted', 'deleted', vm_desc, 'delete and re-download Skythonic', printouts)
    #print('<<Re-Installing Skythonic>>')
    vm.install_Skythonic(vm_desc, '~/Skythonic', printouts=False)
    #print('<<DONE Re-Installing Skythonic>>')
    covert.danger_copy_keys_to_vm(vm_desc, '~/Skythonic', printouts=False)

    _jump_ssh_cmd_test(out, 'cd ~/Skythonic/softwareDump\n ls -a', 'BYOC_keypair.pem', vm_desc, 'test softwareDump', printouts)

    _jump_ssh_cmd_test(out, 'cd ~/Skythonic/\npython3\nx=1944+2018\nprint(x)\nquit()', str(1944+2018), vm_desc, 'test py shell', printouts)

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
