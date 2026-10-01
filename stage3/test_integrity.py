from pathlib import Path
from integrity_checker import check_integrity
import shutil, sys

B=Path(__file__).parent/"fixtures"
W=Path(__file__).parent/"work"; W.mkdir(exist_ok=True)

cases=[]

def add(name, final_src, expected_src, should_pass, target=True, out_name="result.ods", expected_name=None):
    if expected_name is None: expected_name=out_name
    actual=W/out_name
    shutil.copy2(B/final_src,actual)
    expected_path=W/expected_name
    if expected_path!=actual:
        if expected_path.exists(): expected_path.unlink()
    result=check_integrity(
        final_path=actual,
        expected_semantic_path=B/expected_src,
        target_verifier_pass=target,
        expected_output_path=expected_path,
    )
    got=result["PASS"]
    ok=(got==should_pass)
    cases.append((name,ok,got,should_pass,result))
    print(f"{name}: EXPECTED={should_pass} GOT={got} {'PASS' if ok else 'FAIL'} {result}")

add("legal_cell_edit","final_cell_ok.ods","expected_cell.ods",True)
add("side_effect_other_cell","final_side_cell.ods","expected_cell.ods",False)
add("side_effect_sheet_deleted","final_sheet_deleted.ods","expected_cell.ods",False)
add("side_effect_extra_row","final_extra_row.ods","expected_cell.ods",False)
add("side_effect_formula_lost","final_formula_lost.ods","expected_cell.ods",False)
add("legal_sort","final_sort_ok.ods","expected_sort.ods",True)
add("legal_insert_row","final_insert_ok.ods","expected_insert.ods",True)
add("legal_delete_row","final_delete_ok.ods","expected_delete.ods",True)
add("legal_copy","final_copy_ok.ods","expected_copy.ods",True)
add("legal_move","final_move_ok.ods","expected_move.ods",True)
add("metadata_only_ignored","final_metadata_only.ods","expected_cell.ods",True)
add("author_date_view_cursor_ignored","meta_noisy.ods","meta_expected.ods",True)
add("target_verifier_fail","final_cell_ok.ods","expected_cell.ods",False,target=False)
add("wrong_output_name","final_cell_ok.ods","expected_cell.ods",False,out_name="wrong_name.ods",expected_name="expected_name.ods")
add("wrong_format","invalid_format.ods","expected_cell.ods",False)

legal=[c for c in cases if c[0].startswith("legal_") or c[0] in ("metadata_only_ignored","author_date_view_cursor_ignored")]
illegal=[c for c in cases if c not in legal]
legal_ok=sum(1 for c in legal if c[1])
illegal_ok=sum(1 for c in illegal if c[1])
fp=sum(1 for _,ok,got,exp,_ in cases if got and not exp)
fn=sum(1 for _,ok,got,exp,_ in cases if (not got) and exp)
print(f"LEGAL_MUTATIONS_ACCEPTED={legal_ok}/{len(legal)}")
print(f"INJECTED_SIDE_EFFECTS_DETECTED={illegal_ok}/{len(illegal)}")
print(f"FALSE_POSITIVES={fp}")
print(f"FALSE_NEGATIVES={fn}")
gate=(legal_ok==len(legal) and illegal_ok==len(illegal) and fp==0 and fn==0)
print("STAGE3_INTEGRITY_GATE=PASS" if gate else "STAGE3_INTEGRITY_GATE=FAIL")
sys.exit(0 if gate else 1)
