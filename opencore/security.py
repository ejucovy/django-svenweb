def get_permission_constraints(policy_or_request, role):
    PERMISSION_CONSTRAINTS = {
    'open_policy': {
        "Anonymous": ["WIKI_VIEW", "WIKI_HISTORY"],
        "Authenticated": ["WIKI_VIEW", "WIKI_HISTORY", "WIKI_EDIT"],
        "ProjectMember": ["WIKI_VIEW", "WIKI_HISTORY",
                          "WIKI_EDIT", "WIKI_CONFIGURE", "WIKI_DEPLOY"],
        "WikiManager": ["WIKI_VIEW", "WIKI_HISTORY",
                        "WIKI_EDIT", "WIKI_CONFIGURE", "WIKI_DEPLOY"],
        "ProjectAdmin": ["WIKI_VIEW", "WIKI_HISTORY",
                         "WIKI_EDIT", "WIKI_CONFIGURE", "WIKI_DEPLOY"],
        },
    'medium_policy': {
        "Anonymous": ["WIKI_VIEW", "WIKI_HISTORY"],
        "Authenticated": ["WIKI_VIEW", "WIKI_HISTORY"],
        "ProjectMember": ["WIKI_VIEW", "WIKI_HISTORY",
                          "WIKI_EDIT", "WIKI_CONFIGURE", "WIKI_DEPLOY"],
        "WikiManager": ["WIKI_VIEW", "WIKI_HISTORY",
                        "WIKI_EDIT", "WIKI_CONFIGURE", "WIKI_DEPLOY"],
        "ProjectAdmin": ["WIKI_VIEW", "WIKI_HISTORY",
                         "WIKI_EDIT", "WIKI_CONFIGURE", "WIKI_DEPLOY"],
        },
    'closed_policy': {
        "Anonymous": [],
        "Authenticated": [],
        "ProjectMember": ["WIKI_VIEW", "WIKI_HISTORY",
                          "WIKI_EDIT", "WIKI_CONFIGURE", "WIKI_DEPLOY"],
        "WikiManager": ["WIKI_VIEW", "WIKI_HISTORY",
                        "WIKI_EDIT", "WIKI_CONFIGURE", "WIKI_DEPLOY"],
        "ProjectAdmin": ["WIKI_VIEW", "WIKI_HISTORY",
                         "WIKI_EDIT", "WIKI_CONFIGURE", "WIKI_DEPLOY"],
        },
    }
    if isinstance(policy_or_request, basestring):
        policy = policy_or_request
    else:
        policy = policy_or_request.get_security_policy()
    return PERMISSION_CONSTRAINTS[policy][role]

def get_highest_role(roles):
    for role in (
        "ProjectAdmin",
        "WikiManager",
        "ProjectMember",
        "Authenticated",
        "Anonymous",
        ):
        if role in roles:
            return role

