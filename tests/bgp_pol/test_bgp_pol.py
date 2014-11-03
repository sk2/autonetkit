from autonetkit.plugins.bgp_pol import pol_to_json
import os

policies = [
"if (tags contain aaa and prefix_list is zyx and tags contain bbb) then (reject and setLP 100)",
"if (tags contain aaa and prefix_list is zyx and tags contain bbb) then (reject and setLP 100) else (setLP 200)",
"if (prefix_list is ccc) then (reject and setLP 100) else (reject and setMED 240 and setLP 210)",
("if (prefix_list is ccc) then (reject and setLP 100) else "
    "(if (prefix_list is ccc) then (setLP 120) else (setMED 230))"),
"if (prefix_list is ccc) then (setLP 120) else (setMED 230))",
"reject and setLP 200",
]

for index, policy in enumerate(policies):
    result = pol_to_json(policy)
    dirname, filename = os.path.split(os.path.abspath(__file__))
    policy_filename = os.path.join(dirname, "policy_%s.txt" % index )

    with open(policy_filename, "r") as fh:
        expected = fh.read()

    assert(result == expected)
