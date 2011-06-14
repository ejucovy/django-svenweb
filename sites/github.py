from github2.client import Github

class GithubSite(object):
    """
    Adapts Wiki objects
    """
    def __init__(self, wiki):
        self.wiki = wiki

    def repo(self):
        repo = self.wiki.github_repo()
        assert "/" in repo
        return repo

    def push_url(self, domain="github.com"):
        return "git@%s:%s.git" % (domain, self.repo())

    def repo_exists(self):
        github = Github(requests_per_second=1)
        try:
            repo = github.repos.show(self.repo())
        except RuntimeError:
            return False
        return True

    def ghpages_exists(self):
        github = Github(requests_per_second=1)
        try:
            branches = github.repos.branches(self.repo())
        except RuntimeError:
            return False
        return 'gh-pages' in branches

    def create_repo(self, username, token):
        """
        Returns True if creation succeeds.
        Returns False if user is unauthorized.
        Raises underlying exception otherwise.
        """
        assert not self.repo_exists()

        repo = self.repo()
        # If user joe is creating repo joe/site.git 
        # the repo path has to just be "site.git".
        # Apparently the full path is only used
        # if you're interacting with a repo outside
        # the authenticated user's path.
        if repo.split("/")[0] == username:
            repo = repo.split("/")[1]

        github = Github(requests_per_second=1,
                        username=username, api_token=token)
        try:
            repo = github.repos.create(repo)
        except RuntimeError, exc:
            if "401" in exc.args[0]:  # todo: not fine-grained enough to identify auth failure
                return False
            raise
        return True
