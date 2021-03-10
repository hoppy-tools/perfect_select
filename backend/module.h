#ifndef PERFECT_SELECT_MODULE_H
#define PERFECT_SELECT_MODULE_H

#define TARGET_PY_MODULE_COMPOSE_NX(A, B) A ## B
#define TARGET_PY_MODULE_COMPOSE(B) TARGET_PY_MODULE_COMPOSE_NX(PyInit_, B)(void)

// extern stubs
extern "C" {
void _BLI_assert_print_pos(const char *file, const int line, const char *function, const char *id) {};
void _BLI_assert_print_backtrace(void) {};
void _BLI_assert_abort(void) {};
}

#endif //PERFECT_SELECT_MODULE_H
