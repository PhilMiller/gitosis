import os, logging
from ConfigParser import NoSectionError, NoOptionError

from gitosis import group

def getOwnerAccess(config, mode, path):
    """
    Returns the owner user for the relevant repository, if access
    is granted for this mode. The 'owner' option must refer to an
    existing user section.

    Returns None if no owner is available for this path and mode.
    """
    try:
        accessible = config.getboolean('gitosis', 'owner-%s' % mode)
    except (NoSectionError, NoOptionError):
        accessible = False

    if accessible:
        try:
            owner = config.get('repo %s' % path, 'owner')
            if config.has_section('user %s' % owner):
                return owner
        except (NoSectionError, NoOptionError):
            pass


def haveAccess(config, user, mode, path):
    """
    Map request for write access to allowed path.

    Note for read-only access, the caller should check for write
    access too.

    Returns ``None`` for no access, or a tuple of toplevel directory
    containing repositories and a relative path to the physical repository.
    """
    log = logging.getLogger('gitosis.access.haveAccess')

    log.debug(
        'Access check for %(user)r as %(mode)r on %(path)r...'
        % dict(
        user=user,
        mode=mode,
        path=path,
        ))

    basename, ext = os.path.splitext(path)
    if ext == '.git':
        log.debug(
            'Stripping .git suffix from %(path)r, new value %(basename)r'
            % dict(
            path=path,
            basename=basename,
            ))
        path = basename

    try:
        default_prefix = config.get('gitosis', 'repositories')
    except (NoSectionError, NoOptionError):
        default_prefix = 'repositories'

    sections = ['group %s' % item for item in
                 group.getMembership(config=config, user=user)]
    sections.insert(0, 'user %s' % user)

    for sectname in sections:
        try:
            repos = config.get(sectname, mode)
        except (NoSectionError, NoOptionError):
            repos = []
        else:
            repos = repos.split()

        mapping = None

        if path in repos:
            log.debug(
                'Access ok for %(user)r as %(mode)r on %(path)r'
                % dict(
                user=user,
                mode=mode,
                path=path,
                ))
            mapping = path
        else:
            try:
                mapping = config.get(sectname,
                                     'map %s %s' % (mode, path))
            except (NoSectionError, NoOptionError):
                pass
            else:
                log.debug(
                    'Access ok for %(user)r as %(mode)r on %(path)r=%(mapping)r'
                    % dict(
                    user=user,
                    mode=mode,
                    path=path,
                    mapping=mapping,
                    ))

        if mapping is None and mode == 'readonly':
            try:
                if config.getboolean(sectname, 'allow-read-all'):
                    log.debug(
                        'Access ok for %(user)r as %(mode)r on %(path)r via allow-read-all'
                        % dict(user=user,mode=mode,path=path))
                    mapping = path
            except (NoSectionError, NoOptionError):
                pass

        if mapping is not None:
            prefix = None
            try:
                prefix = config.get(sectname, 'repositories')
            except (NoSectionError, NoOptionError):
                prefix = default_prefix

            log.debug(
                'Using prefix %(prefix)r for %(path)r'
                % dict(
                prefix=prefix,
                path=mapping,
                ))
            return (prefix, mapping)

    owner = getOwnerAccess(config, mode, path)
    if owner == user:
        try:
            prefix = config.get('user %s' % owner, 'repositories')
        except (NoSectionError, NoOptionError):
            prefix = default_prefix

        log.debug(
            'Access ok for %(user)r as %(mode)r on owned %(path)r, using prefix %(prefix)r'
            % dict(
                prefix=prefix,
                path=path,
                user=user,
                mode=mode,
                ))
        return (prefix, path)


def cacheAccess(config, mode, cache):
    """
    Computes access lists for all repositories in one pass.
    """
    for sectname in config.sections():
        GROUP_PREFIX = 'group '
        USER_PREFIX  = 'user '
        REPO_PREFIX  = 'repo '
        if sectname.startswith(USER_PREFIX):
            idx = 0
            name = sectname[len(USER_PREFIX):]
        elif sectname.startswith(GROUP_PREFIX):
            idx = 1
            name = sectname[len(GROUP_PREFIX):]
        elif sectname.startswith(REPO_PREFIX):
            # Single repository: handle owner
            name = sectname[len(REPO_PREFIX):]
            if (mode,name) not in cache:
                cache[mode,name] = (set(),set())

            owner = getOwnerAccess(config, mode, name)
            if owner is not None:
                cache[mode,name][0].add(owner)
            continue

        else:
            continue

        try:
            repos = config.get(sectname, mode)
        except (NoSectionError, NoOptionError):
            repos = []
        else:
            repos = repos.split()

        for (iname, ivalue) in config.items(sectname):
            if iname.startswith('map %s ' % mode):
                repos.append(ivalue)

        if mode == 'readonly':
            try:
                if config.getboolean(sectname, 'allow-read-all'):
                    repos.append(None)
            except (NoSectionError, NoOptionError):
                pass

        for path in repos:
            if (mode,path) not in cache:
                cache[mode,path] = (set(),set())

            cache[mode,path][idx].add(name)


def listAccess(config, table, mode, path, users, groups):
    """
    List users and groups who can access the path.

    Note for read-only access, the caller should check for write
    access too.
    """

    basename, ext = os.path.splitext(path)
    if ext == '.git':
        path = basename

    if (mode,path) in table:
        (cusers, cgroups) = table[mode,path]
        users.update(cusers)
        groups.update(cgroups)

    if (mode,None) in table:
        (cusers, cgroups) = table[mode,None]
        users.update(cusers)
        groups.update(cgroups)


def getAccessTable(config,modes=['readonly','writable','writeable']):
    """
    A trivial helper that builds ACL table for all repositories
    and given set of modes.
    """
    table = dict()
    for mode in modes:
        cacheAccess(config,mode,table)

    return table


def getAllAccess(config,table,path,modes=['readonly','writable','writeable']):
    """
    Returns access information for a certain repository.
    """
    users = set()
    groups = set()
    for mode in modes:
        listAccess(config,table,mode,path,users,groups)

    all_refs = set(['@'+item for item in groups])
    for grp in groups:
        group.listMembers(config,grp,all_refs)

    return (users, groups, all_refs)
