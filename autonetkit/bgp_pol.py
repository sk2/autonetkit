from pyparsing import Suppress,Word,ZeroOrMore,alphas,nums,delimitedList, Literal, Group


class pol_conditional(object):
    pass

class pol_if(pol_conditional):
    def __repr__(self):
        return "if"

class pol_then(pol_conditional):
    def __repr__(self):
        return "then"

class pol_else(pol_conditional):
    def __repr__(self):
        return "else"

class pol_match(object):
    pass


def fn_if(strg, loc, toks):
    print "tokens are", toks

# Matches


def fn_match_tags(strg, loc, toks):
    #print strg, loc, toks
    pass

def fn_match_pl(strg, loc, toks):
    #print strg, loc, toks
    pass

class pol_action(object):
    pass

# Actions
def fn_set_lp(strg, loc, toks):
    #print strg, loc, toks
    pass

def fn_reject(strg, loc, toks):
    print strg, loc, toks

my_policy = "if (tags contain aaa) then (setLP 100)"

if_token = Literal("if").setParseAction( lambda x: pol_if())
then_token = Literal("then").setParseAction( lambda x: pol_then())
else_token = Literal("else").setParseAction( lambda x: pol_else())

and_token = Literal("and")
is_token = Literal("is")

# matches
# tags contain xyz
match_tags = Group(Literal("tags contain") + Word(alphas)).setParseAction(fn_match_tags)
match_pl = Group(Literal("prefix_list") + is_token + Word(alphas)).setParseAction(fn_match_tags)

# advanced matches (need to be expanded)
# origin(...)
# transit(...)

# actions
# setLP lp
token_set_lp = Group(Literal("setLP") + Word(nums)).setParseAction(fn_set_lp)
# setMED med
# addTag tag
# removeTag tag
# reject
token_reject = Literal("reject").setParseAction(fn_reject)

# these can either take an IP or a host - todo: do we also want to allow specifying interface?
# setNextHop ip | host
# setOriginAttribute ip | host


#token_policy = (if_token + match_tags + then_token + token_set_lp)
#results = token_policy.parseString(my_policy)

match_clause = (match_tags | match_pl)
match_clauses = match_clause + ZeroOrMore(and_token + match_clause)
if_clause = Group(Literal("if") + Suppress("(") + match_clauses + Suppress(")")).setParseAction(fn_if)
my_policy = "if (tags contain aaa and prefix_list is zyx)"
results = if_clause.parseString(my_policy)

print "results", results

# Now have a list of tokens, these need to be parsed into a AST



# also need to walk tree to build up a list of all tags present, and all prefix lists
