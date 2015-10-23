# =-------------- 
# sequence Monad
# =--------------
def flatten(listOfLists):
    "Flatten one level of nesting"
    assert isinstance(listOfLists, list)
    if len(listOfLists) > 0:
        assert isinstance(listOfLists[0], list)
    return [x for sublist in listOfLists for x in sublist]

# sequence monad
def seq_unit(x): return [x]
def seq_bind(mval, mf): return flatten(map(mf, mval))

# Decompose ErrorT e m a
def get_value(m_val): return m_val[0]
def get_error(m_val): return m_val[1]

# hard coded "(ErrorT e) List a" instance of throwError, note that seq_unit is hardcoded
def error_throwError(err): return (None, err)
def errorT_list_throwError(err): return seq_unit(error_throwError(err))

# "(ErrorT e) List a" monad
def error_unit(x): return (x,None)
def errorT_list_unit(x): return seq_unit(error_unit(x))

def error_bind(mval, mf):
    assert isinstance(mval, tuple)
    error = get_error(mval)
    if error:
        return error_throwError(error)
    else: 
        return mf(get_value(mval))

# Cannot have multi-line lambda
def errorT_list_bind_helper(mval, mf):
    assert isinstance(mval, tuple)
    error = get_error(mval)
    if error:
        return errorT_list_throwError(error)
    else: 
        return mf(get_value(mval))

def errorT_list_bind(mval, mf): return seq_bind(mval, lambda v: errorT_list_bind_helper(v, mf))

# combined monad !! (ErrorT e) List a
unit = errorT_list_unit
bind = errorT_list_bind
throwError = errorT_list_throwError

# hard coded "lift :: List a -> (ErrorT e) List a"
def lift(mval):
    assert isinstance(mval, list)
    # return [ (val,None) for val in mval ]
    # return [ errorT_list_unit(val) for val in mval ]
    return seq_bind(mval, lambda v : unit(v))


# End of sequence Monad


