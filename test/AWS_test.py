import AWS.AWS_query as AWS_query

def test_ssh_jumpbox():
    # Tests: A: is everything installed.
    #        B: Are the scp files actually copied over.
    vm = AWS_query.get_by_name('machine', 'BYOC_jumpbox_VM')
    if vm is None:
        raise Exception('Cant find BYOC_jumpbox_VM to test on. Is it named differently or not set up?')
    print(vm)
    return False
