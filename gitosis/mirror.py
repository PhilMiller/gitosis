"""
Created on 23 Mar 2009

@author: Damien Lebrun
"""
from ConfigParser import NoOptionError, NoSectionError
import os
import logging

from gitosis import repository
from gitosis import util


def push_mirrors(config, git_dir):
    """
    Apply a push with the mirror option to all mirrors defined in gitosis.conf
    of the repository being updated.
    
    @param config: ConfiParser object loaded with gitosis.conf
    @param git_dir: Path the repository being updated. 
    """
    log = logging.getLogger('gitosis.mirror.push_mirrors')
    
    repository_dir = os.path.abspath(util.getRepositoryDir(config))
    git_dir = os.path.abspath(git_dir)
    git_name = get_git_name(repository_dir, git_dir)
    
    log.info('Updating %s\'s mirrors.' % git_name)
    
    for remote in get_mirrors(config, git_name):
        log.info('Updating %s.' % remote)
        repository.mirror(git_dir, remote)

        
def get_git_name(repository_dir, git_dir):
    """
    Guess the name of the repository used in gitosis.conf
    from the name of the git directory name:
    
    /path/to/foo.git => foo
    
    @param repository_dir: path to gitosis directory of repository
    @param git_dir: path to repository being updated. 
    
    """
    if git_dir.startswith(repository_dir):
        git_name = git_dir[len(repository_dir):]
    else:
        git_name = os.path.split(git_dir)[1]
        
    git_name = git_name.strip(r'\/')     
    if git_name.endswith('.git'):
        git_name = git_name[:-4]
    return git_name

def get_mirrors(config, git_name):
    """
    Get a repository mirror list from gitosis.conf.
    
    @param config: ConfigParser object
    @param git_name: the name of the repository  
    """
    for mirror in get_repo_section_mirrors(config, git_name):
        yield mirror
    
    for uri, repos in get_mirror_sections(config):
        for repo in repos:
            if repo in ('@all', git_name,):
                yield uri % git_name
                    
def get_repo_section_mirrors(config, git_name):
    """
    Get the list of mirrors set in a repo section
    
    @param config: ConfigParser object
    @param git_name: the name of the repository
    @return generator  
    """
    try:
        mirrors = config.get('repo %s' % git_name, 'mirrors')
        for mirror in mirrors.split():
            yield mirror
    except (NoSectionError, NoOptionError):
        pass

def get_mirror_sections(config):
    """
    Get the list of all mirror sections.
    
    Return a list of uri and repositories set in each section
    
    @param config: ConfigParser object
    @return generator 
    """
    
    log = logging.getLogger('gitosis.mirror.get_mirror_sections')
    mirror_sections = (s for s in config.sections() if s.startswith('mirror '))
    for section in mirror_sections:
        try:
            uri =  config.get(section, 'uri').strip()
            repos = config.get(section, 'repos').split()
            yield uri, util.getExplicitRepositoryNames(config, repos)
        except NoOptionError:
            log.error('%s section is lacking the "repos" or "uri" settings.', section)