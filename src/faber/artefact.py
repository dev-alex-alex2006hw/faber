#
# Copyright (c) 2016 Stefan Seefeld
# All rights reserved.
#
# This file is part of Faber. It is made available under the
# Boost Software License, Version 1.0.
# (Consult LICENSE or http://www.boost.org/LICENSE_1_0.txt)

from __future__ import absolute_import
from . import types
from .feature import set
from .delayed import delayed_property
from .utils import path_formatter, add_metaclass
from . import logging
from os.path import normpath, join
from collections import defaultdict
from functools import reduce

scheduler_logger = logging.getLogger('scheduler')
feature_logger = logging.getLogger('features')

intermediate= 0x0001
nocare= 0x0002
notfile= 0x0004
always= 0x0008
leaves= 0x0010
noupdate= 0x0020
rmold= 0x0080
internal=0x0100
precious= 0x0200
nopropagate = 0x0400


class artefact(object):
    """An artefact can be generated by a build."""

    _path_formatter = path_formatter()
    _qnames = defaultdict(list)

    @staticmethod
    def finish():
        artefact._qnames.clear()

    @staticmethod
    def iter():
        """Iterate over all registered artefacts."""

        return iter(a for qname in artefact._qnames.values() for a in qname)

    @staticmethod
    def lookup(qname):
        """Find an artefact by (qualified) name."""

        if qname not in artefact._qnames:
            raise KeyError(qname)
        else:
            return artefact._qnames[qname]

    @classmethod
    def instantiate(cls, a, module=None):
        return a if isinstance(a, artefact) else cls(a, module=module)

    @staticmethod
    def combine_use(artefacts):
        """return the union of the use features from all artefacts"""
        return reduce(lambda fs, a: fs|a.use, artefacts, set())

    @property
    def qname(self):
        """The qualified name of this artefact."""
        return self.module.qname(self.name)

    @property
    def id(self):
        """Yield a unique identifier for this artefact."""
        return '%s-%x' % (self.qname, id(self))

    @property
    def isfile(self):
        """Just a convenience property for a frequent query"""
        return not self.attrs & notfile

    @property
    def relpath(self):
        """The relative path corresponding to the artefact's feature set."""
        f = artefact._path_formatter
        return normpath(f.format(self.path_spec, **self.features))

    @property
    def _filename(self):
        """The (full) filename of this artefact, if it represents a file."""
        return normpath(join(self.module.builddir, self.relpath, self.name))

    @delayed_property
    def filename(self):
        return self._filename

    @property
    def boundname(self):
        """Return either self.filename or self.qname depending on whether
        this artefact represents a file."""
        return self._filename if self.isfile else self.qname

    def __init__(self, name, attrs=0, type=None, module=None,
                 features=(), use=(), condition=None,
                 path_spec='',
                 logfile=None):
        self.name = name
        from .module import module as M
        self.module = module or M.current
        self.attrs = attrs
        self.path_spec = path_spec
        self.features = self.module.features | set.instantiate(features)
        self.use = set.instantiate(use)
        self.condition = condition
        self.status = None
        self.type = type
        if not self.type and self.isfile:
            # just a guess, subclasses may override
            self.type = types.type.discover(self._filename)
        self.logfile = logfile
        self._register()

    def __call__(self, features):
        """Clone this artefact, and apply new features."""

        import copy
        clone = copy.copy(self)
        clone.features = self.features.copy()
        clone.features.update(set.instantiate(features))
        clone._register()
        return clone

    def update(self):
        from . import scheduler
        return scheduler.update(self)

    def reset(self):
        self.status = None

    def _register(self):
        from . import scheduler
        artefact._qnames[self.qname].append(self)
        scheduler.define_artefact(self)
        deps = self.features.dependencies()
        if deps:
            scheduler.add_dependency(self, deps)

    def __str__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.qname)

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self.id)

    def __status__(self, status):
        self.status = status


class source_type(type):
    def __call__(cls, name, *args, **kwds):
        """Make sure there is only one instance per source (file)."""
        from .module import module as M
        module = kwds.get('module') or M.current
        qname = module.qname(name)
        if qname not in cls._instances:
            cls._instances[qname] = type.__call__(cls, name, *args, **kwds)
        return cls._instances[qname]


@add_metaclass(source_type)
class source(artefact):
    """A source is a simple feature-less artefact representing an existing
    file outside faber's control."""

    _instances = {}

    def _register(self):
        # don't depend on anything
        from . import scheduler
        artefact._qnames[self.qname].append(self)
        scheduler.define_artefact(self, bind=True)

    @property
    def _filename(self):
        return join(self.module.srcdir, self.name)


class conditional(artefact):

    def __init__(self, a, condition, features=()):
        artefact.__init__(self, 'c:' + a.name, features=features,
                          attrs=notfile, condition=condition, module=a.module)
        self.a = a
        self.dependent = []  # set by depend()

    def reset(self):
        # do not reset this artefact as we can't undo its action
        pass

    def __status__(self, status):
        artefact.__status__(self, status)
        result = self.condition(self.features.eval(update=False))
        feature_logger.info('condition "{}" yields {}'
                            .format(self.condition, result))
        if result:
            from . import scheduler
            for d in self.dependent:
                scheduler.add_dependency(d, self.a)


def init():
    """reset globals"""

    source._instances.clear()
