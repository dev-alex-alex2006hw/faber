#
# Copyright (c) 2016 Stefan Seefeld
# All rights reserved.
#
# This file is part of Faber. It is made available under the
# Boost Software License, Version 1.0.
# (Consult LICENSE or http://www.boost.org/LICENSE_1_0.txt)

from ..artefact import artefact
from ..artefacts.library import library
from ..tool import tool
from ..feature import feature, multi, path, incidental
from os.path import basename, join
from importlib import import_module
import logging

logger = logging.getLogger(__name__)

cppflags = feature('cppflags', attributes=multi|incidental)
define = feature('define', attributes=multi|incidental)
include = feature('include', attributes=multi|path|incidental)
cflags = feature('cflags', attributes=multi|incidental)
cxxflags = feature('cxxflags', attributes=multi|incidental)
ldflags = feature('ldflags', attributes=multi|incidental)
link = feature('link', ['static', 'shared'])
linkpath = feature('linkpath', attributes=multi|path|incidental)
libs = feature('libs', attributes=multi|incidental)
target = feature('target', os=feature(), arch=feature())

class compiler(tool):

    path_spec = '{compiler.name}-{compiler.version}/{target.arch}/{link}/'

    @classmethod
    def split_libs(cls, sources):
        """split libraries from sources.
        Return (src, linkpath, libs)"""

        src = []
        libs = []
        linkpath = set()
        for s in sources:
            if type(s) is str:
                src.append(s)
            elif isinstance(s, library):
                libs.append(basename(s.name))
                linkpath.add(join(s.module.builddir, s.path))
            elif isinstance(s, artefact):
                src.append(s.bound_name)
            else:
                raise ValueError('Unknown type of source {}'.format(s))
        return src, linkpath, libs

def try_instantiate(name, fs=None):

    try:
        mod = import_module('.{}'.format(name), 'faber.tools')
        getattr(mod, name)(features=fs)
    except Exception as e:
        logger.debug('trying to instantiate {} yields "{}"'
                     .format(name, e))