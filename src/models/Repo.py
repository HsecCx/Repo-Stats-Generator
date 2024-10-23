class Repo:
    def __init__(self, public_git_url, name, languages, public_scm, public_url):
        self.public_git_url = public_git_url
        self.name = name
        self.languages = languages  
        self.public_scm = public_scm  
        self.public_url = public_url
        self.lines_of_code = None  # Future state

    def to_dict(self):
        """Convert the repository object to a dictionary format suitable for JSON, excluding None values."""
        # Return a dictionary representation of instance variables, excluding None values and private/special variables.
        return {key: value for key, value in self.__dict__.items() if value is not None and not key.startswith('_')}