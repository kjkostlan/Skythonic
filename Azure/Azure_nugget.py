# The initialization is much harder than AWS boto3.
import subprocess
from waterworks import plumber
try:
    from azure.identity import AzureCliCredential
    from azure.mgmt.network.models import VirtualNetwork, AddressSpace, Subnet
    from azure.mgmt.resource.resources.models import ResourceGroup
    from azure.mgmt.network import NetworkManagementClient
    from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient
    from azure.mgmt.compute import ComputeManagementClient
    from azure.mgmt.storage import StorageManagementClient
except Exception as e:
    raise Exception('Some pip packages may be missing:'+str(e))

def get_subscription_id():
    # No easy way around a bash call:
    the_id = subprocess.check_output("az account show --query 'id' -o tsv", shell=True)
    return the_id.decode('utf-8').strip()

def try_versions(f, *args, **kwargs):
    # We have to guess the API versions. Different functions have different API versions!
    versions = ['2023-04-01', '2023-04-02', '2023-07-01'] # TODO: fill out with the latest for all the different programmers.
    for v in versions:
        kwargs['api_version'] = v
        try:
            return f(*args, **kwargs)
        except Exception as e:
            if 'and API version' in str(e):
                pass # We guessed wrong.
            else:
                raise e
    print('Uh no API version works here, lets see the list of valid versions:')
    f(*args, **kwargs)

def basic_looptry(f, msg):
    def f_catch(e):
        txt = str(e)
        return 'Failed to invoke the Azure CLI' in txt or 'is in progress' in txt
    return plumber.loop_try(f, f_catch, msg, delay=1)

try: # One-time setup.
    _subs_id
except:
    _subs_id = get_subscription_id()
    credential = AzureCliCredential()
    network_client = NetworkManagementClient(credential, _subs_id)
    resource_client = ResourceManagementClient(credential, _subs_id)
    subscription_client = SubscriptionClient(credential)
    skythonic_rgroup_name = 'Skythonic_resource_group'
    storage_client = StorageManagementClient(credential, _subs_id)

    subscription = subscription_client.subscriptions.get(_subs_id)
    all_locations = [x.name for x in list(subscription_client.subscriptions.list_locations(_subs_id))]

    token = credential.get_token("https://graph.microsoft.com/.default")
    #tenant_id = token.tenant_id # No attribute called tenant_id
    #authority = f"https://login.microsoftonline.com/{tenant_id}"
    #client_id = credential.get_token("https://graph.microsoft.com/.default").claims.get("appid")
    #client_secret = credential.get_token(client_id, ["https://management.azure.com/.default"]).token
    compute_client = ComputeManagementClient(credential, _subs_id)
    #app = ConfidentialClientApplication(client_id, authority=authority, client_credential=client_secret)
    #token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    #policy_client = PolicyInsightsClient(credential) # Package not found.
