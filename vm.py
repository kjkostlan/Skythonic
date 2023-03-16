# Tools for keeping track of virtual machines, such as the login keys.
# See: https://stackoverflow.com/questions/51026026/how-to-pass-private-key-as-text-to-ssh
# Don't forget the chmod 600 on the keys!
# And the fun of scp: https://www.simplified.guide/ssh/copy-file
import pickle

fname = './softwareDump/vm_info.pypickle'
tmp_key_file = './softwareDump/tmp_key.pem'

def _pickleload():
    TODO
def _picklesave():
    TODO

def update_vms_skythonic(diff):
    # Updates all skythonic files on VMs.
    # Diff can be a partial or full update.
    TODO

def danger_key(instance_id, key_material):
    # Saves the private key's material unencrypted. Be careful out there!
    TODO

def set_key_file(instance_id):
    # Sets the tmp key .pem file to the instances key. Must be saved with danger_key.
    TODO
