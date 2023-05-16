# Tools to set up some common kinds of resources
import boto3
import AWS.AWS_core as AWS_core
import AWS.AWS_query as AWS_query
import AWS.AWS_format as AWS_format
import vm, eye_term
import time
import covert, plumbing
ec2r = boto3.resource('ec2'); ec2c = boto3.client('ec2'); iam = boto3.client('iam')

def simple_vm(vm_name, private_ip, subnet_id, securitygroup_id, key_name):
    # Creates a new key if need be, but the subnet and securitygroup must be already made.
    # Returns inst_id, None, fname.
    inst_networkinter = [{'SubnetId': subnet_id, 'DeviceIndex': 0, 'PrivateIpAddress': private_ip,
                          'AssociatePublicIpAddress': False, 'Groups': [securitygroup_id]}]
    # ami-0735c191cf914754d; ami-0a695f0d95cefc163; ami-0fcf52bcf5db7b003
    vm_params = {'ImageId':vm.ubuntu_aim_image(), 'InstanceType':'t2.micro',
                 'MaxCount':1, 'MinCount':1,'NetworkInterfaces':inst_networkinter,
                 'KeyName':key_name}

    return covert.vm_dangerkey(vm_name, vm_params)

def wait_and_attach_address(machine_id, address_id):
    # TODO: build this into the AWS_core function.
    addr = AWS_format.id2obj(address_id)
    if 'InstanceId' in addr:
        if addr['InstanceId']==machine_id:
            print('Address already attached.')
            return
        else:
            raise Exception('Address attached to the wrong machine.')
    f_try = lambda: AWS_core.assoc(addr['AllocationId'], machine_id) #ec2c.associate_address(AllocationId=addr['AllocationId'],InstanceId=inst_id)
    f_catch = lambda e:"The pending instance" in repr(e) and "is not in a valid state" in repr(e)
    msg = 'Waiting for machine: '+machine_id+' to be ready for attached address'
    eye_term.loop_try(f_try, f_catch, msg, delay=4)

def setup_jumpbox(basename='jumpbox', subnet_zone='us-west-2c', user_name='BYOC', key_name='BYOC_keypair'): # The jumpbox is much more configurable than the cloud shell.
    # Note: for some reason us-west-2d fails for this vm, so us-west-2c is the default.
    vpc_id = AWS_core.create_once('VPC', user_name+'_Service', True, CidrBlock='10.200.0.0/16') #vpc = ec2r.create_vpc(CidrBlock='172.16.0.0/16')
    ec2c.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
    ec2c.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})

    webgate_id = AWS_core.create_once('webgate', user_name+'_'+basename+'_gate', True)
    AWS_core.assoc(vpc_id, webgate_id)
    routetable_id = AWS_core.create_once('rtable', user_name+'_'+basename+'_rtable', True, VpcId=vpc_id) # TODO: Use the default one.
    ec2c.create_route(RouteTableId=routetable_id, DestinationCidrBlock='0.0.0.0/0',GatewayId=webgate_id)
    subnet_id = AWS_core.create_once('subnet',user_name+'_'+basename+'_subnet', True, CidrBlock='10.200.250.0/24', VpcId=vpc_id, AvailabilityZone=subnet_zone)
    AWS_core.assoc(routetable_id, subnet_id)
    securitygroup_id = AWS_core.create_once('securitygroup', user_name+'_'+basename+'_sGroup', True, GroupName='SSH-ONLY', Description='only allow SSH traffic', VpcId=vpc_id)
    try:
        ec2c.authorize_security_group_ingress(GroupId=securitygroup_id, CidrIp='0.0.0.0/0', IpProtocol='tcp', FromPort=22, ToPort=22)
    except Exception as e:
        if 'already exists' not in repr(e):
            raise e

    inst_id = simple_vm(user_name+'_'+basename+'_VM', '10.200.250.100', subnet_id, securitygroup_id, key_name)

    addr = AWS_core.create_once('address', user_name+'_'+basename+'_address', True, Domain='vpc')
    wait_and_attach_address(inst_id, addr)
    report, t0 = vm.update_Apt(inst_id, printouts=True, full_restart_here=False)

    ssh_cmd = vm.ssh_cmd(inst_id, True)

    print('---Setting up AWS on the jump box (WARNING: long term AWS credentials posted to VM)---')
    region_name = subnet_zone
    if region_name[-1] in 'abcd':
        region_name = region_name[0:-1]

    tests = [t0]
    for x in [vm.install_python3(inst_id, printouts=True),
              vm.install_AWS(inst_id, user_name, region_name, printouts=True), vm.install_Ping(inst_id, printouts=True),\
              vm.install_Skythonic(inst_id, '~/Skythonic', printouts=True),
              vm.install_netTools(inst_id, printouts=True),
              vm.install_netcat(inst-id, printouts=True),
              vm.install_vim(inst_id, printouts=True),
              vm.install_tcpdump(inst_id, printouts=True),
              vm.install_iputilsPing(inst_id, printouts=True),
              vm.install_hostList(inst_id, printouts=True)]:
        report.append(x[0])
        tests.append(x[1])
    vm.restart_vm(inst_id)

    print('BEGIN JUMBBOX INSTALL TESTS')
    for t in tests:
        t()

    print('Check the above printouts for Apt update, AWS, Ping, and Skythonic intall.')
    print('Use this to ssh:', ssh_cmd)
    print('[Yes past the security warning (safe to do in this particular case) and ~. to leave ssh session.]')
    if len(report.errors)>0:
        print('Possible errors:', report.errors)

    return ssh_cmd, inst_id, report

def setup_threetier(key_name='BYOC_keypair', jbox_name='BYOC_jumpbox_VM', new_vpc_name='BYOC_Spoke1', subnet_zone='us-west-2c'):
    vpc_id = AWS_core.create_once('VPC', new_vpc_name, True, CidrBlock='10.201.0.0/16')
    ec2c.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
    ec2c.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})

    webgate_id = AWS_core.create_once('webgate', new_vpc_name+'_gate', True)
    AWS_core.assoc(vpc_id, webgate_id)

    def _nameget(ty, name):
        x = AWS_query.get_by_name(ty, name)
        if x is None:
            raise Exception(f'Cannot find this name: {name}; make sure setup_jumpbox has been called.')
        return AWS_format.obj2id(x)

    jbox_id = _nameget('machine',jbox_name)
    jbox_subnet_id = AWS_format.id2obj(jbox_id)['SubnetId']
    jbox_vpc_id = AWS_format.id2obj(jbox_subnet_id)['VpcId']
    rtables = AWS_query.get_resources('rtable')
    matching_rtable_ids = []
    for rt in rtables: # TODO: better connectivity querying.
        for a in rt.get('Associations', []):
            if a.get('SubnetId',None)==jbox_subnet_id:
                matching_rtable_ids.append(AWS_format.obj2id(rt))
    if len(matching_rtable_ids)==1:
        jbox_rtable_id = matching_rtable_ids[0]
    elif len(matching_rtable_ids)>1:
        raise Exception('Too many routetables match the Jumbbox.')
    elif len(matching_rtable_ids)==0:
        raise Exception('Too few routetables match the Jumpbox')

    print('Jumpbox machine ID:', jbox_id, jbox_subnet_id, jbox_vpc_id)
    routetable_id = AWS_core.create_once('rtable', new_vpc_name+'_rtable', True, VpcId=vpc_id)

    basenames = ['BYOC_web', 'BYOC_app', 'BYOC_db']
    subnet_cidrs = ['10.201.101.0/24', '10.201.102.0/24', '10.201.103.0/24']
    ips =          ['10.201.101.100',  '10.201.102.100',  '10.201.103.100']
    inst_ids = []
    cmds = []
    for i in range(3):
        ec2c.create_route(RouteTableId=routetable_id, DestinationCidrBlock='0.0.0.0/0',GatewayId=webgate_id)
        subnet_id = AWS_core.create_once('subnet',basenames[i], True, CidrBlock=subnet_cidrs[i], VpcId=vpc_id, AvailabilityZone=subnet_zone)
        AWS_core.assoc(routetable_id, subnet_id)

        # They have different security groups for different types of servers, so we will do so as well rather than use only one for all three:
        #https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html
        securitygroup_id = AWS_core.create_once('securitygroup', basenames[i]+'_sGroup', True, GroupName='From Hub'+basenames[i], Description='Allow Hub Ip cidr', VpcId=vpc_id)
        try:
            ec2c.authorize_security_group_ingress(GroupId=securitygroup_id, CidrIp='10.0.0.0/8', IpProtocol='-1', FromPort=22, ToPort=22)
        except Exception as e:
            if 'already exists' not in repr(e):
                raise e
        if i==0: # BYOC_web accepts https traffic from https (port 443).
            ec2c.authorize_security_group_ingress(GroupId=security_group_id, IpProtocol='tcp', FromPort=443, ToPort=443, CidrIp='0.0.0.0/0')

        inst_id = simple_vm(basenames[i], ips[i], subnet_id, securitygroup_id, key_name)
        inst_ids.append(inst_id)

    for i in range(3): # Break up the loops so that the instances are bieng started up concurrently.
        addr = AWS_core.create_once('address', basenames[i]+'_address', True, Domain='vpc')
        wait_and_attach_address(inst_ids[i], addr)
        vm.update_Apt(inst_ids[i], printouts=True, full_restart_here=False)
        cmds.append(vm.ssh_cmd(inst_ids[i], True))

    for i in range(3):
        inst_id = inst_ids[i]
        vm.install_mysqlClient(inst_id, printouts=True)
        vm.install_netTools(inst_id, printouts=True)
        vm.install_netcat(inst-id, printouts=True)
        vm.install_vim(inst_id, printouts=True)
        vm.install_tcpdump(inst_id, printouts=True)
        vm.install_iputilsPing(inst_id, printouts=True)
    vm.install_appServerCmds(inst_ids[1])
    vm.install_apache(inst_ids[0])
    vm.install_webServerCmds(inst_ids[0])

    print('Restarting the three new vms.')
    vm.restart_vm(inst_ids)

    #The gateway is the VpcPeeringConnectionId
    peering_id = AWS_core.create_once('vpcpeer', 'BYOC_3lev_peer', True, VpcId=jbox_vpc_id, PeerVpcId=vpc_id) #AWS_core.assoc(jbox_vpc_id, vpc_id)
    rtables = ec2c.describe_route_tables()['RouteTables']

    print("Creating route on hub rtable id:", jbox_rtable_id)
    try:
        ec2c.create_route(RouteTableId=jbox_rtable_id, DestinationCidrBlock='10.201.0.0/16',GatewayId=peering_id)
    except Exception as e:
        if 'already exists' not in repr(e):
            raise e

    print("Creating route on Spoke1 rtable id:", routetable_id)
    try:
        ec2c.create_route(RouteTableId=routetable_id, DestinationCidrBlock='10.200.0.0/16',GatewayId=peering_id)
    except Exception as e:
        if 'already exists' not in repr(e):
            raise e

    # Testing time:
    jbox_id = AWS_format.obj2id(plumbing.flat_lookup(AWS_query.get_resources('machine'), 'VpcId', jbox_vpc_id, assert_range=[1, 65536])[0])
    print(f'Testing ssh ping from machine {jbox_id}')

    #TODO: C. Test the peering connection and routing by pinging the VMs web, app, and db, from the jumpbox.
    is_ssh = True # TODO: True in the cloud shell, False if we are in the jumpbox.
    tubo = vm.patient_ssh_pipe(jbox_id, printouts=True) if is_ssh else eye_term.MessyPipe('bash', None, printouts=True)
    tubo.API('ping -c 2 localhost')
    for ip in ips:
        cmd = f'ping -c 2 {ip}'
        tubo.API(cmd, timeout=16)

    tubo.close()

    txt = str(tubo.history_contents)
    if 'packet loss' not in txt:
        print('WARNING: Cant extract ping printout to test.')
    elif '50% packet loss' in txt or '100% packet loss' in txt:
        print('WARNING: Packets lost in test')

    print('Check the above ssh ping test')
    return cmds
