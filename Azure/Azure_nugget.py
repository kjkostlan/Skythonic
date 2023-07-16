# It's much harder than boto3.
import subprocess
try:
    from azure.identity import AzureCliCredential
    from azure.mgmt.network.models import VirtualNetwork, AddressSpace, Subnet
    from azure.mgmt.network import NetworkManagementClient
    from azure.mgmt.resource import ResourceManagementClient
except Exception as e:
    raise Exception('Some pip packages may be missing:'+str(e))

def get_subscription_id():
    # No easy way around a bash call:
    the_id = subprocess.check_output("az account show --query 'id' -o tsv", shell=True)
    return the_id.decode('utf-8').strip()

try: # One-time setup.
    _subs_id
except:
    _subs_id = get_subscription_id()
    credential = AzureCliCredential()
    network_client = NetworkManagementClient(credential, get_subscription_id())
    resource_client = ResourceManagementClient(credential, get_subscription_id())
