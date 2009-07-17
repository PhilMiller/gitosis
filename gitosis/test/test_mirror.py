from nose.tools import eq_ as eq, ok_ as ok

from ConfigParser import RawConfigParser
from StringIO import StringIO
from copy import deepcopy
import os

from gitosis import mirror, repository
from gitosis.test.util import maketemp

CONFIG = """
[gitosis]
public = bar baz
private = foo fu/bar

[group admin]
members = alice
writable = gitosis @private @public 

[repo foo]
mirrors = /var/www/foo /var/trac/foo/repo

[repo bar]
mirrors= /var/www/bar

[mirror github]
uri = git@github.com:alice/%s.git
repos = @public

[mirror gitorious]
uri = git@gitorious.org:%s/mainline.git
repos = @public
"""

BACKUP_EXTRA_CONFIG = """
[mirror backup]
uri = git@backup.example.com:repositories/%s.git
repos = @all
"""

def get_config(extra=''):
    cfg = RawConfigParser()
    cfg.readfp(StringIO(CONFIG + extra))
    return cfg

def test_push_mirrors():
    tmp = maketemp()
    foo_path = os.path.join(tmp, 'foo.git')
    copy1_path = os.path.join(tmp, 'copy1.git')
    copy2_path = os.path.join(tmp, 'copy2.git')
    cfg = get_config()
    cfg.set('gitosis', 'repositories', tmp)
    cfg.set('repo foo', 'mirrors', ' '.join([copy1_path,copy2_path]))
    ## create foo repository and its mirrors (leave the mirror empty
    repository.init(path=foo_path, template=False)
    repository.init(path=copy1_path, template=False)
    repository.init(path=copy2_path, template=False)
    repository.fast_import(
        git_dir=foo_path,
        commit_msg='foo initial bar',
        committer='Mr. Unit Test <unit.test@example.com>',
        files=[
            ('foo', 'bar\n'),
            ],
        )
    
    ## push changes to mirror
    mirror.push_mirrors(cfg, foo_path)
    
    ## check content of mirrors
    export_copy1 = os.path.join(tmp, 'export1')
    repository.export(
        git_dir=copy1_path,
        path=export_copy1,
        )
    eq(os.listdir(export_copy1),
       ['foo'])
    
    export_copy2 = os.path.join(tmp, 'export2')
    repository.export(
        git_dir=copy2_path,
        path=export_copy2,
        )
    eq(os.listdir(export_copy2),
       ['foo'])
    
def test_get_git_name():
    eq('foo', mirror.get_git_name('/home/git/repository', '/home/git/repository/foo.git'))
    eq('fu/bar', mirror.get_git_name('/home/git/repository', '/home/git/repository/fu/bar.git'))

def test_get_mirrors_from_repo_section():
    mirrors = list(mirror.get_mirrors(get_config(), 'foo'))
    ok('/var/www/foo' in mirrors)
    ok('/var/trac/foo/repo' in mirrors)
    eq(2, len(mirrors))
    
def test_get_mirrors_from_mirror_section():
    mirrors = list(mirror.get_mirrors(get_config(), 'baz'))
    ok('git@github.com:alice/baz.git' in mirrors)
    ok('git@gitorious.org:baz/mainline.git' in mirrors)
    eq(2, len(mirrors))
    
def test_get_mirrors_from_mirror_and_repo_sections():
    mirrors = list(mirror.get_mirrors(get_config(), 'bar'))
    ok('git@github.com:alice/bar.git' in mirrors)
    ok('git@gitorious.org:bar/mainline.git' in mirrors)
    ok('/var/www/bar' in mirrors)
    eq(3, len(mirrors))

def test_get_mirrors_with_all():
    cfg = get_config(extra=BACKUP_EXTRA_CONFIG)
    mirrors = list(mirror.get_mirrors(cfg, 'foo'))
    ok('/var/www/foo' in mirrors)
    ok('/var/trac/foo/repo' in mirrors)
    ok('git@backup.example.com:repositories/foo.git' in mirrors)
    eq(3, len(mirrors))

def test_get_repo_section_mirrors():
    mirrors = list(mirror.get_repo_section_mirrors(get_config(), 'foo'))
    ok('/var/www/foo' in mirrors)
    ok('/var/trac/foo/repo' in mirrors)
    eq(2, len(mirrors))

def test_get_mirror_sections():
    mirrors = list(
        mirror.get_mirror_sections(
            get_config(extra=BACKUP_EXTRA_CONFIG)))
    uri_list = []
    for uri, repos in mirrors:
        uri_list.append(uri)
        repos = list(repos)
        if uri == 'git@backup.example.com:repositories/%s.git':
            ok('@all' in repos)
            eq(1, len(repos))
        else:
            ok('bar' in repos)
            ok('baz' in repos)
            eq(2, len(repos))
    ok('git@github.com:alice/%s.git' in uri_list)
    ok('git@gitorious.org:%s/mainline.git' in uri_list)
    ok('git@backup.example.com:repositories/%s.git' in uri_list)
    eq(3, len(mirrors))