#include <Python.h>

#include "select.h"
#include "module.h"


static PyObject *extend_to_edge_loops(PyObject *self, PyObject *args) {
    uintptr_t contextPointer;
    uintptr_t operatorPointer;

    PyObject* result = PySet_New(NULL);

    if (!PyArg_ParseTuple(args, "kk", &contextPointer, &operatorPointer)) {
        PySet_Add(result, PyUnicode_FromString("CANCELLED"));
        return result;
    }

    if (extend_to_edge_loops_exe(contextPointer, operatorPointer)) {
        PySet_Add(result, PyUnicode_FromString("FINISHED"));
    } else {
        PySet_Add(result, PyUnicode_FromString("CANCELLED"));
    }
    return result;
}

static PyObject *perfect_select(PyObject *self, PyObject *args) {
    uintptr_t contextPointer;
    uintptr_t operatorPointer;

    PyObject* result = PySet_New(NULL);

    if (!PyArg_ParseTuple(args, "kk", &contextPointer, &operatorPointer)) {
        PySet_Add(result, PyUnicode_FromString("CANCELLED"));
        return result;
    }

    return result;
}

static PyMethodDef PerfectSelectBackendMethods[] = {
    { "extend_to_edge_loops", extend_to_edge_loops, METH_VARARGS, "Extend To Edge Loops" },
    { "perfect_select", perfect_select, METH_VARARGS, "Perfect Select" },
    { NULL, NULL, 0, NULL }
};

static struct PyModuleDef PerfectSelectBackendBackendModule = {
    PyModuleDef_HEAD_INIT,
    "perfect_select_backend",
    "C/C++ Backend for perfect_select",
    -1,
    PerfectSelectBackendMethods
};

PyMODINIT_FUNC TARGET_PY_MODULE_COMPOSE(PERFECT_SELECT_MODULE_NAME)
{
    return PyModule_Create(&PerfectSelectBackendBackendModule);
}
