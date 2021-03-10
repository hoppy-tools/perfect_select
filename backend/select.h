#ifndef PERFECT_SELECT_SELECT_H
#define PERFECT_SELECT_SELECT_H

#include "bl_integration.h"

bool extend_to_edge_loops_exe(uintptr_t contextPointer, uintptr_t operatorPointer);

void tag_loop(BMesh *bm, char test_flag, char enable_flag);
void tag_region_to_loop(BMesh *bm, char test_flag, char enable_flag);

void tag_faces_in_to_boundary_loop(BMesh *bm, char boundary_flag, char loops_flag, char enable_flag);
void tag_faces_out_to_boundary_loop(BMesh *bm, char boundary_flag, char loops_flag, char enable_flag);
void faces_out_to_boundary_loop_iter_loops(BMesh *bm, BMFace *f, BMEdge **edarray, int &totedgetag,
                                            const char boundary_flag, const char loops_flag, const char enable_flag);

#endif //PERFECT_SELECT_SELECT_H
