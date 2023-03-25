# (This could be a mini project)
# Shell is centered around a human seeing things, and it feeds streams.
# The human often has to respond mid stream with "y" to continue, for example, or timeout if things are taking too long.
# Programming languages, on the other hand, are sequential at thier core (often with tools to multitask).
# *Of course* the 2023+ solution is AI, but this one should be fairly simple.
#https://www.linode.com/docs/guides/use-paramiko-python-to-ssh-into-a-server/
#https://hackersandslackers.com/automate-ssh-scp-python-paramiko/
import time, re

class MessyPipe:
    # The low-level basic messy pipe object with a way to get [output, error] as a string.
    def __init__(self, client):
        # TODO: switchyard on the type of pipe.
        self.client = client
        self.ctype = str(type(client))
        self.channel = None
        self.streams = None
        self.t0 = time.time() # Time since last clear.
        self.t1 = time.time() # Time of last sucessful read.
        if 'paramiko.client.SSHClient' in self.ctype:
            self.channel = client.invoke_shell()
            self.channel.settimeout(0.125)
            # TODO: What is the stdout vs stderr.
            self.streams = [self.channel.makefile_stdin('wb'), self.channel.makefile('rb'), self.channel.makefile_stderr('rb')]#, self.channel.makefile('rb')]

            chan = client.get_transport().open_session()
            self.contents = ['',''] # Output and error.
            self.history_contents = ['',''] # Includes history.
            self.cmd_history = []

            self.close = lambda: client.close()
        else:
            raise Exception("Unknown client type:"+str(type(client)))
        # https://stackoverflow.com/questions/40451767/paramiko-recv-ready-returns-false-values
        #https://gist.github.com/kdheepak/c18f030494fea16ffd92d95c93a6d40d

    def update(self):
        _out = None; _err = None
        if 'paramiko.client.SSHClient' in self.ctype:
            def _read(file_like_obj):
                out = []
                while True:
                    try:
                        out.append(file_like_obj.read(1).decode())
                    except Exception as e:
                        if 'timeout()' not in repr(e):
                            raise e
                        break
                if len(out)>0:
                    self.t1 = time.time()
                return ''.join(out)
            use_read = False
            if use_read:
                print('Read line:', self.streams[1].readline(), self.streams[2].readline())
                TODO
            else:
                _out = _read(self.streams[1])
                _err = _read(self.streams[2])
                # print('Dir:', dir(self.streams[1]))
                #if self.streams[1].readable():
                #    _out = self.streams[1].read(16).decode()
                #if self.streams[2].readable():
                #    _err = self.streams[2].read(16).decode()
        else:
            raise Exception('This code currently does not understand: '+self.ctype)
        new_stuff = [_out, _err]
        for i in range(len(new_stuff)):
            if new_stuff[i] is not None:
                self.contents[i] = self.contents[i]+new_stuff[i]

    def empty(self, remove_history=False):
        self.t0 = time.time()
        self.history_contents = [self.history_contents[i]+self.contents[i] for i in range(len(self.contents))]
        self.contents = ['' for _ in self.contents]
        if remove_history:
            self.history_contents = []; self.cmd_history = []

    def drought_len(self):
        return time.time() - self.t1

    def send(self, txt):
        # The non-blocking operation.
        #https://stackoverflow.com/questions/6203653/how-do-you-execute-multiple-commands-in-a-single-session-in-paramiko-python
        self.cmd_history.append(txt)
        if 'paramiko.client.SSHClient' in self.ctype:
            self.streams[0].write(txt+'\n')
        else:
            raise Exception('This code currently does not understand: '+self.ctype)

    def API(self, txt, f_poll=None, dt_min=0.0001, dt_max=1):
        # Sents the command, then calls f_poll(self) repedably with gradually increasing dt.
        # When f_poll returns True it will return the result and clear self.
        # A default f_poll if it is None
        self.send(txt)
        dt = dt_min
        if f_poll is None:
            f_poll = standard_is_done
        while not f_poll(self):
            time.sleep(dt)
            dt = min(dt*1.414, dt_max)
            self.update()
        out = self.contents.copy()
        self.empty()
        return out

    def multi_API(self, cmds, f_poll=None, dt_min=0.0001, dt_max=1):
        # For simplier series of commands.
        # Returns output, errors. f_poll can be a list of fns 1:1 with cmds.
        outputs = []; errs = []
        self.empty()
        for i in range(len(cmds)):
            f_poll1 = f_poll[i] if (type(f_poll) is list or type(f_poll) is tuple) else f_poll
            out, err = self.API(cmds[i], f_poll=f_poll1, dt_min=dt_min, dt_max=dt_max)
            outputs.append(out)
            errs.append(err)
        return outputs, errs

    def sure_of_EOF(self):
        # Only if we are sure! Not all that useful since it isn't often triggered.
        # Note: this fn doesn't seem to be reliable.
        if 'paramiko.client.SSHClient' in self.ctype:
            #https://stackoverflow.com/questions/35266753/paramiko-python-module-hangs-at-stdout-read
            #print('The dir:', dir(self.streams[1]))
            ended_list = [False, False] # TODO: fix this.
            #ended_list = [self.streams[1].eof_received(), self.streams[2].eof_received()]
            return len(list(filter(lambda x: x, ended_list)))==len(ended_list)

def many_lines(the_pipe):
    txt = ''.join(the_pipe.history_contents[0])+the_pipe.contents[0]
    txt = txt.replace('\r\n','\n').strip()
    return filter(lambda x: len(x)>0, txt.split('\n'))

def likely_prompts(lines, include_fails=True):
    # Guesses the (most recent) shell prompt thing that prepends each line.
    # This can change i.e. if you enter a Python session.
    patterns = [r'[#>\$]', r'continue\? *\[Y\/n\]']
    out = []
    for l in lines: # There are more efficient ways if speed becomes a problem here.
        passed = False
        for the_pattern in patterns:
            ixs = [x.end() for x in re.finditer(the_pattern, l)]
            if len(ixs)>0:
                out.append(l[0:ixs[-1]])
                passed = True
                break
        if include_fails and not passed:
            out.append(None)
    return out

def basic_wait(p, timeout=4):
    # A simple waiting function. TODO: bundle into a larger heuristic.
    return p.sure_of_EOF() or p.drought_len()>timeout

def basic_expect_fn(the_pattern, is_re=True):
    # A standard expect fn based on text. Only looks for stuff in the last command.
    def _expt(p):
        txt = ''.join(self.contents) # Mash the out and err together.
        return re.search(the_pattern, txt) is not None if is_re else the_pattern in txt
    return _expt

def standard_is_done(p):
    # A default works-most-of-the-time pipe dryness detector.
    # Will undergo a lot of tweaks that try to extract the spatial information.
    all_lines = many_lines(p)
    timeout_s = 8
    prompts = likely_prompts(all_lines, True); t = p.drought_len()
    if len(prompts)==0 or len(''.join(p.contents).strip())==0:
        return t>timeout_s
    sent_cmds = p.cmd_history
    return t>timeout_s or prompts[-1] is not None

def termstr(_out, _err):
    # Prints it in a format that is easier to read.
    pieces = []
    for i in range(len(_out)):
        pieces.append(_out[i])
        if _err is not None:
            pieces.append(_err[i])
    txt = '\n'.join(pieces)
    txt = txt.replace('\r\n','\n')
    txt = txt.replace('\n\n','\n')
    return txt
