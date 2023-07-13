# Misc formatting.

def enumr(txt0): # ENUMerate Resourse type. Different clouds may call it by different names.
    txt = txt0.strip().lower().replace('_','')
    if txt[-1] == 's':
        txt = txt[0:-1]
    TODO
    raise Exception(f'{txt0} is not an understood Azure resource ID nor type.')

def obj2id(obj_desc): # Gets the ID from a description.
    if type(obj_desc) is str:
        return obj_desc
    TODO

def id2obj(the_id, assert_exist=True):
    if type(the_id) is dict:
        return the_id # Already a description.
    TODO

def tag_dict(desc_or_id):
    desc = id2obj(desc_or_id)
    TODO
    return out
