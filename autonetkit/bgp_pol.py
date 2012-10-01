from pyparsing import Suppress,Word,ZeroOrMore,alphas,nums,delimitedList, Literal, Group, Optional, Forward

#TODO: see if can just use t for the functions rather than strc, loc, toks
#TODO: generate all of the "boilerplate" classes and match functions from YAML or other description
#TODO: consider the switch to lambda x: with __init__ rather than a function and a class
#TODO: add in parse fail handling for more descriptive error messages

class pol_conditional(object):
    pass

class pol_match_or_action(object):
    is_match = False
    is_then = False
    is_else = False

class pol_if(pol_conditional):
    def __init__(self, match_clause = None, then_clause = None, else_clause = None):
        self.match_clause = match_clause
        self.then_clause = then_clause
        self.else_clause = else_clause

    def __repr__(self):
        if self.else_clause:
            return "If:\n%s\n%s\n%s" % (self.match_clause, self.then_clause, self.else_clause)
        return "If:\n %s\n %s" % (self.match_clause, self.then_clause)

class pol_then(pol_conditional):
    def __repr__(self):
        return "then"

class pol_else(pol_conditional):
    def __repr__(self):
        return "else"

def fn_if(strg, loc, toks):
# Extract matches and actions - need to search through list. Return first (only) instance
    print "toks", toks
    match_clause = [tok for tok in toks[0] if tok.is_match][0]
    then_clause = [tok for tok in toks[0] if tok.is_then][0]
    try:
        else_clause = [tok for tok in toks[0] if tok.is_else][0]
    except IndexError:
        else_clause = None
    return pol_if(match_clause, then_clause, else_clause)

class pol_match(pol_match_or_action):
    def __init__(self, matches):
        self.is_match = True
        self.matches = matches

    def __repr__(self):
        return "Match: %s" % self.matches

class pol_match_tag(object):
    def __init__(self, tag):
        self.tag = tag

    def __repr__(self):
        return "tags contain %s" % self.tag

class pol_match_pl(object):
    def __init__(self, pl):
        self.pl = pl

    def __repr__(self):
        return "prefix_list is %s" % self.pl

# Matches

def fn_match(strg, loc, toks):
    matches = toks[0]
    return pol_match(matches)

def fn_match_tags(strg, loc, toks):
    tag = toks[0][1]
    return pol_match_tag(tag)

def fn_match_pl(strg, loc, toks):
    pl = toks[0][2]
    return pol_match_pl(pl)

class pol_then(pol_match_or_action):
    def __init__(self, actions):
        self.is_then = True
        self.actions = actions

    def __repr__(self):
        return "Then: %s" % self.actions

class pol_else(pol_match_or_action):
    def __init__(self, actions):
        self.is_else = True
        self.actions = actions

    def __repr__(self):
        return "Else: %s" % self.actions

# Actions
class pol_set_lp(object):
    def __init__(self, pl):
        self.pl = pl

    def __repr__(self):
        return "setLP %s" % self.pl

class pol_set_med(object):
    def __init__(self, med):
        self.med = med

    def __repr__(self):
        return "setMED %s" % self.med

class pol_add_tag(object):
    def __init__(self, tag):
        self.tag = tag

    def __repr__(self):
        return "addTag %s" % self.tag

class pol_remove_tag(object):
    def __init__(self, tag):
        self.tag = tag

    def __repr__(self):
        return "removeTag %s" % self.tag

class pol_reject(object):
    def __init__(self):
        pass # no parameter for reject route

    def __repr__(self):
        return "reject" 

def fn_then(strg, loc, toks):
    actions = toks[0]
    return pol_then(actions)

def fn_else(strg, loc, toks):
    actions = toks[0]
    return pol_else(actions)

def fn_set_lp(strg, loc, toks):
    lp = toks[0][1]
    return pol_set_lp(lp)

def fn_set_med(strg, loc, toks):
    med = toks[0][1]
    return pol_set_med(med)

def fn_add_tag(strg, loc, toks):
    tag = toks[0][1]
    return pol_add_tag(tag)

def fn_remove_tag(strg, loc, toks):
    tag = toks[0][1]
    return pol_remove_tag(tag)

def fn_reject(strg, loc, toks):
    return pol_reject()

and_token = Suppress("and")
is_token = Literal("is")

# matches
# tags contain xyz
match_tags = Group(Literal("tags contain") + Word(alphas)).setParseAction(fn_match_tags)
match_pl = Group(Literal("prefix_list") + is_token + Word(alphas)).setParseAction(fn_match_pl)

# advanced matches (need to be expanded)
#TODO: expand these as match... and use memoize decorator to cache the search query
# origin(...)
# transit(...)

match_clause = (match_tags | match_pl)
match_clauses = Group(Suppress("(") + match_clause + ZeroOrMore(and_token + match_clause) 
        + Suppress(")")).setParseAction(fn_match)

# actions
# setLP lp
token_set_lp = Group(Literal("setLP") + Word(nums)).setParseAction(fn_set_lp)
# setMED med
token_set_med = Group(Literal("setMed") + Word(nums)).setParseAction(fn_set_med)
# addTag tag
token_add_tag = Group(Literal("addTag") + Word(nums)).setParseAction(fn_add_tag)
# removeTag tag
token_remove_tag = Group(Literal("removeTag") + Word(nums)).setParseAction(fn_remove_tag)
# reject
token_reject = Literal("reject").setParseAction(fn_reject)

# these can either take an IP or a host - todo: do we also want to allow specifying interface?
# setNextHop ip | host
# setOriginAttribute ip | host

action_clause = (token_set_lp | token_set_med | token_add_tag | token_remove_tag | token_reject ) 
then_clause = Group(Suppress("then") + Suppress("(") + action_clause + ZeroOrMore(and_token + action_clause) 
        + Suppress(")")).setParseAction(fn_then)

else_clause = Group(Suppress("else") + Suppress("(") + action_clause + ZeroOrMore(and_token + action_clause) 
        + Suppress(")")).setParseAction(fn_else)

if_clause = Group(Suppress("if") + match_clauses + then_clause).setParseAction(fn_if)
my_policy = "if (tags contain aaa and prefix_list is zyx and tags contain bbb) then (reject and setLP 100)"
results = if_clause.parseString(my_policy)
print "results", results

#my_policy = "if (tags contain aaa ) then (if (prefix_list is ccc) then (reject and setLP 100))"
my_policy = "if (prefix_list is ccc) then (reject and setLP 100) else (reject)"
results = if_clause.parseString(my_policy)
print "results", results


# Now have a list of tokens, these need to be parsed into a AST



# also need to walk tree to build up a list of all tags present, and all prefix lists


# end up with lists of named tuples for tokens: (match, value), and (action, value) that can then format inside the template - that way slight differences between syntaxes are able to be handles in templates rather than back up in the parser
