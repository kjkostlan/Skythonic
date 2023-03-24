
import sys, time
import install_core, file_io

def _importcode(mnames):
    return ['import '+mname for mname in mnames]

def awsP(windows=False):
    imports = ['AWS.AWS_core as AWS_core','AWS.AWS_clean as AWS_clean','AWS.AWS_setup as AWS_setup','AWS.AWS_query as AWS_query', 'boto3']
    lines = _importcode(imports)
    lines = lines+["ec2r = boto3.resource('ec2')", "ec2c = boto3.client('ec2')", 'who = AWS_query.get_resources']
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

def azureP(windows=False):
    lines = [] # TODO
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

def googleP(windows=False):
    lines = [] # TODO
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

# All these below are lower prority (<=5%)
#https://www.statista.com/chart/18819/worldwide-market-share-of-leading-cloud-infrastructure-service-providers/
def alibabaP(windows=False):
    lines = [] # TODO
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

def ibmP(windows=False):
    lines = [] # TODO
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

def salesforceP(windows=False):
    lines = [] # TODO
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

def tencentP(windows=False):
    lines = [] # TODO
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

def oracleP(windows=False):
    lines = [] # TODO
    exec(install_core.joinlines(lines, windows), vars(sys.modules['__main__']))

if __name__ == '__main__': # For running on your local machine.
    import clipboard #pip install clipboard on your machine, no need on the Cloud Shell.
    from itertools import islice

    def batched(iterable, n): #https://docs.python.org/3/library/itertools.html
        "Batch data into tuples of length n. The last batch may be shorter."
        # batched('ABCDEFG', 3) --> ABC DEF G
        if n < 1:
            raise ValueError('n must be at least one')
        it = iter(iterable)
        while True: # The := is as of Python 3.8 and had to be removed.
            batch = tuple(islice(it, n))
            if not batch:
                break
            yield batch

    while True:
        #install_txt(windows=False, diff=False, pyboot_txt=True, import_txt=True)
        cache_before_input = install_core.src_cache_from_disk()

        x = input('<None> = load diffs, a = load all, a1/4 = load the 2nd quarter of files (size constraints of paste); q = quit.').lower().strip()
        if x=='q':
            quit()
        cache_afr_input = install_core.src_cache_from_disk()
        cache_diff = install_core.src_cache_diff(old_cache=cache_before_input, new_cache=cache_afr_input)

        a = 0 # For beaking down large pastes.
        if x.startswith('a'):
            all_files = cache_afr_input
            if '/' in x: # Only include some files.
                pieces = x.strip().replace('a','').split('/')
                kys = list(all_files.keys()); kys.sort()
                a = int(pieces[0]); b = int(pieces[1])
                sz = int(len(kys)/b+len(kys)/(len(kys)+1))
                pieces1 = list(batched(kys, sz))
                if len(pieces1) != b:
                    raise Exception('bug in this code.')
                piece = pieces1[a]
                pickle_these = dict(zip(piece, [all_files[k] for k in piece]))
            else:
                pickle_these = all_files
        else:
            pickle_these = cache_diff

        big_txt = file_io.pickle64(pickle_these)
        n = len(pickle_these)

        txt = install_core.bootstrap_txt(False, big_txt, pyboot_txt=a==0 and 'a' in x, import_txt=True)
        clipboard.copy(txt)
        if n==0:
            print('No pickled files but code has been copied to jumpstart your Python work.')
        else:
            print(f'Your clipboard is ready with: {n} pickled files; {list(pickle_these.keys())}; press enter once pasted in or c to cancel')
        install_core.update_src_cache() # Not sure if necessary.
