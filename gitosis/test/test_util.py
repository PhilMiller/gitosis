"""
Created on 12 Apr 2009

@author: damien
"""
from nose.tools import eq_ as eq, ok_ as ok

from ConfigParser import RawConfigParser
from gitosis import util

def test_getAliasRepos():
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'foo', 'bar baz')
    repos = list(util.getAliasRepositories(cfg, 'foo'))
    ok('bar' in repos)
    ok('baz' in repos)
    eq(2, len(repos))
    
    cfg.set('gitosis', 'foobar', '@foo foo')
    repos = list(util.getAliasRepositories(cfg, 'foobar'))
    ok('bar' in repos)
    ok('baz' in repos)
    ok('foo' in repos)
    eq(3, len(repos))
    
def test_getExplicitRepoNames():
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'foo', 'bar baz')
    repos = list(util.getExplicitRepositoryNames(cfg, ['@foo', 'foo']))
    ok('bar' in repos)
    ok('baz' in repos)
    ok('foo' in repos)
    eq(3, len(repos))