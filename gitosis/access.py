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


def listAccess(config, mode, path, users, groups):
    """
    List users and groups who can access the path.

    Note for read-only access, the caller should check for write
    access too.
    """

    basename, ext = os.path.splitext(path)
    if ext == '.git':
        path = basename

    for sectname in config.sections():
        GROUP_PREFIX = 'group '
        USER_PREFIX  = 'user '
        if sectname.startswith(GROUP_PREFIX):
            out_set = groups
            name = sectname[len(GROUP_PREFIX):]
        elif sectname.startswith(USER_PREFIX):
            out_set = users
            name = sectname[len(USER_PREFIX):]
        else:
            continue

        try:
            repos = config.get(sectname, mode)
        except (NoSectionError, NoOptionError):
            repos = []
        else:
            repos = repos.split()

        if path in repos:
            out_set.add(name)
        else:
            for (iname, ivalue) in config.items(sectname):
                if ivalue == path and iname.startswith('map %s ' % mode):
                    out_set.add(name)

        if mode == 'readonly':
            try:
                if config.getboolean(sectname, 'allow-read-all'):
                    out_set.add(name)
            except (NoSectionError, NoOptionError):
                pass


    owner = getOwnerAccess(config, mode, path)
    if owner is not None:
        users.add(owner)


def getAllAccess(config,path,modes=['readonly','writable','writeable']):
    """
    Returns access information for a certain repository.
    """
    users = set()
    groups = set()
    for mode in modes:
        listAccess(config,mode,path,users,groups)

    all_refs = set(['@'+item for item in groups])
    for grp in groups:
        group.listMembers(config,grp,all_refs)

    return (users, groups, all_refs)
