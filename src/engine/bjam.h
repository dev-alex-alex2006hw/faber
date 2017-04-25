/*
 * Copyright (c) 2016 Stefan Seefeld
 * All rights reserved.
 *
 * This file is part of Faber. It is made available under the
 * Boost Software License, Version 1.0.
 * (Consult LICENSE or http://www.boost.org/LICENSE_1_0.txt)
 */
#ifndef engine_bjam_h_
#define engine_bjam_h_

#include "lists.h"

#ifdef HAVE_PYTHON

PyObject *list_to_python(LIST * l);
LIST *list_from_python(PyObject * l);

void bjam_init();

#endif
#endif
