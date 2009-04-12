import logging
import errno
import os
from ConfigParser import NoSectionError, NoOptionError

def mkdir(*a, **kw):
    try:
        os.mkdir(*a, **kw)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise

def getRepositoryDir(config):
    repositories = os.path.expanduser('~')
    try:
        path = config.get('gitosis', 'repositories')
    except (NoSectionError, NoOptionError):
        repositories = os.path.join(repositories, 'repositories')
    else:
        repositories = os.path.join(repositories, path)
    return repositories

def getGeneratedFilesDir(config):
    try:
        generated = config.get('gitosis', 'generate-files-in')
    except (NoSectionError, NoOptionError):
        generated = os.path.expanduser('~/gitosis')
    return generated

def getSSHAuthorizedKeysPath(config):
    try:
        path = config.get('gitosis', 'ssh-authorized-keys-path')
    except (NoSectionError, NoOptionError):
        path = os.path.expanduser('~/.ssh/authorized_keys')
    return path

def getExplicitRepositoryNames(config, repos):
    """
    Given a list of repository names or repository aliases,
    return a list of repository names.
    
    @param config: ConfigParser object
    @param repos: List of repository names or aliases
    @return generator  
    """
    
    for name in repos:
        if name == '@all':
            yield '@all'
        elif name.startswith('@'):
            for repo in getAliasRepositories(config, name[1:]):
                yield repo
        else:
            yield name

def getAliasRepositories(config, alias_name):
    """
    Return the list of repository defined in an alias.
    
    @param config:  ConfigParser object
    @param alias_name:  an alias defined in the gitosis section of config 
    """
    log = logging.getLogger('gitosis.mirror.get_mirror_sections')
    try:
        repos_and_aliases = config.get('gitosis', alias_name).split()    
        for repo_or_alias in repos_and_aliases:
            if repo_or_alias.startswith('@'):
                for repo in getAliasRepositories(config, repo_or_alias[1:]):
                    yield repo
            else:
                yield repo_or_alias
    except (NoSectionError, NoOptionError):
        log.error('Alias "%s" not defined in gitosis.conf', alias_name)