from modelgate._checkers import balance, duplicate, integrity, structure

# Order matches spec §5 — also the order RequirementResults appear in a Report.
_NORMATIVE_CHECKERS = [structure, integrity, duplicate, balance]


def get_normative_checkers() -> list:
    return list(_NORMATIVE_CHECKERS)
