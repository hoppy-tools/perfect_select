#include "select.h"

//
// Extend to edge loops functions
//

bool extend_to_edge_loops_exe(uintptr_t contextPointer, uintptr_t operatorPointer) {
    auto *C = reinterpret_cast<bContext *>(contextPointer);
    auto *op = reinterpret_cast<wmOperator *>(operatorPointer);

    bool prop_inner = RNA_boolean_get(op->ptr, "inner");

    Depsgraph *depsgraph = CTX_data_depsgraph_pointer(C);
    ViewLayer *view_layer = CTX_data_view_layer(C);

    uint objects_len = 0;
    Object **objects = BKE_view_layer_array_from_objects_in_edit_mode_unique_data(view_layer, CTX_wm_view3d(C),
                                                                                  &objects_len);
    for (uint ob_index = 0; ob_index < objects_len; ob_index++) {
        Object *obedit = objects[ob_index];
        BMEditMesh *em = BKE_editmesh_from_object(obedit);

        tag_region_to_loop(em->bm, BM_ELEM_SELECT, BM_ELEM_TAG);
        tag_loop(em->bm, BM_ELEM_TAG, BM_ELEM_INTERNAL_TAG);
        if (prop_inner)
            tag_faces_in_to_boundary_loop(em->bm, BM_ELEM_TAG, BM_ELEM_INTERNAL_TAG, BM_ELEM_SELECT);
        else
            tag_faces_out_to_boundary_loop(em->bm, BM_ELEM_TAG, BM_ELEM_INTERNAL_TAG, BM_ELEM_SELECT);

        DEG_id_tag_update(&obedit->id, ID_RECALC_GEOMETRY);
        WM_event_add_notifier(C, NC_GEOM | ND_SELECT, obedit->data);
    }
    MEM_freeN(objects);
    return true;
}

void tag_loop(BMesh *bm, const char test_flag, const char enable_flag)
{
    BMEdge *eed;
    BMEdge **edarray;
    int edindex;
    BMIter iter;
    int totedgetag = 0;

    BM_mesh_elem_hflag_disable_all(bm, BM_EDGE, enable_flag, false);

    BM_ITER_MESH (eed, &iter, bm, BM_EDGES_OF_MESH) {
        if (BM_elem_flag_test(eed, test_flag)) {
            totedgetag++;
        }
    }

    if (totedgetag == 0) {
        return;
    }

    edarray = (BMEdge **)MEM_mallocN(sizeof(BMEdge *) * totedgetag, "edge array");
    edindex = 0;

    BM_ITER_MESH (eed, &iter, bm, BM_EDGES_OF_MESH) {
        if (BM_elem_flag_test(eed, test_flag)) {
            edarray[edindex] = eed;
            edindex++;
        }
    }

    for (edindex = 0; edindex < totedgetag; edindex += 1) {
        eed = edarray[edindex];
        BMWalker walker;
        BMW_init(&walker,
                 bm,
                 BMW_EDGELOOP,
                 BMW_MASK_NOP,
                 BMW_MASK_NOP,
                 BMW_MASK_NOP,
                 BMW_FLAG_TEST_HIDDEN,
                 BMW_NIL_LAY);

        BMElem *ele;
        for (ele = (BMElem*)BMW_begin(&walker, eed); ele; ele = (BMElem*)BMW_step(&walker)) {
            BM_elem_flag_enable(ele, enable_flag);
        }
        BMW_end(&walker);
    }

    MEM_freeN(edarray);
}

void tag_region_to_loop(BMesh *bm, const char test_flag, const char enable_flag)
{
    BMFace *f;
    BMIter iter;

    BM_mesh_elem_hflag_disable_all(bm, BM_EDGE, enable_flag, false);

    BM_ITER_MESH (f, &iter, bm, BM_FACES_OF_MESH) {
        BMLoop *l1, *l2;
        BMIter liter1, liter2;

        BM_ITER_ELEM (l1, &liter1, f, BM_LOOPS_OF_FACE) {
            int tot = 0, tottag = 0;

            BM_ITER_ELEM (l2, &liter2, l1->e, BM_LOOPS_OF_EDGE) {
                tot++;
                tottag += BM_elem_flag_test(l2->f, test_flag) != 0;
            }

            if ((tot != tottag && tottag > 0) || (tottag == 1 && tot == 1)) {
                BM_elem_flag_enable(l1->e, enable_flag);
            }
        }
    }
}

void tag_faces_in_to_boundary_loop(BMesh *bm, char boundary_flag, char loops_flag, char enable_flag)
{

}

void tag_faces_out_to_boundary_loop(BMesh *bm, const char boundary_flag, const char loops_flag, const char enable_flag)
{
    BMEdge *ed;
    BMIter editer;

    BMEdge **edarray;
    int edindex;
    int totedgetag;

    edarray = (BMEdge **)MEM_mallocN(sizeof(BMEdge *) * bm->totedge, "edge array");
    edindex = 0;
    totedgetag = 0;

    BM_ITER_MESH (ed, &editer, bm, BM_EDGES_OF_MESH) {
        if (!BM_elem_flag_test(ed, boundary_flag))
            continue;

        BMFace *f;
        BMIter fiter;

        BM_ITER_ELEM(f, &fiter, ed, BM_FACES_OF_EDGE) {
            if (BM_elem_flag_test(f, enable_flag))
                continue;
            faces_out_to_boundary_loop_iter_loops(bm, f, edarray, totedgetag, boundary_flag, loops_flag, enable_flag);
        }
    }

    for(; edindex < totedgetag; edindex++) {
        BMFace *f;
        BMIter fiter;

        BM_ITER_ELEM(f, &fiter, edarray[edindex], BM_FACES_OF_EDGE) {
            if (BM_elem_flag_test(f, enable_flag))
                continue;
            faces_out_to_boundary_loop_iter_loops(bm, f, edarray, totedgetag, boundary_flag, loops_flag, enable_flag);
        }
    }
    MEM_freeN(edarray);
}

void faces_out_to_boundary_loop_iter_loops(BMesh *bm, BMFace *f, BMEdge **edarray, int &totedgetag,
                                           const char boundary_flag, const char loops_flag, const char enable_flag){
    BMLoop *l;
    BMIter liter;

    BM_ITER_ELEM (l, &liter, f, BM_LOOPS_OF_FACE) {
        if (!BM_elem_flag_test(l->e, boundary_flag))
            continue;

        if (BM_elem_flag_test(l->next->e, boundary_flag) || BM_elem_flag_test(l->next->next->e, loops_flag)) {
            BMEdge *fed;
            BMIter fediter;

            if(enable_flag == BM_ELEM_SELECT){
                BM_face_select_set(bm, f, true);
            }
            else {
                BM_elem_flag_enable(f, enable_flag);
            }
            BM_ITER_ELEM(fed, &fediter, f, BM_EDGES_OF_FACE) {
                if(BM_elem_flag_test(fed, boundary_flag)) {
                    BM_elem_flag_disable(fed, boundary_flag);
                }
                else {
                    BM_elem_flag_enable(fed, boundary_flag);
                    edarray[totedgetag] = fed;
                    totedgetag++;
                }
            }
            break;
        }
    }
}
