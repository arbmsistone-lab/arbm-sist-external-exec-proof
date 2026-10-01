from pathlib import Path
from verifier_engine import verify,normalize_formula,normalize_number
import sys
B=Path(__file__).parent/"fixtures"
good=B/"good.ods"; bad=B/"bad.ods"; asc=B/"sorted_asc.ods"; desc=B/"sorted_desc.ods"
renamed=B/"renamed.ods"; copied=B/"copied.ods"; moved=B/"moved.ods"; filtered=B/"filtered.ods"
cases=[
("cell_value_pos",good,{"type":"cell_value","params":{"sheet":"Vendas","row":2,"col":2,"expected":25}},True),
("cell_value_neg",bad,{"type":"cell_value","params":{"sheet":"Vendas","row":2,"col":2,"expected":25}},False),
("cell_text_pos",good,{"type":"cell_text","params":{"sheet":"Vendas","row":2,"col":1,"expected":"Teclado"}},True),
("row_exists_pos",good,{"type":"row_exists","params":{"sheet":"Vendas","col":1,"value":"Teclado"}},True),
("row_exists_neg",good,{"type":"row_exists","params":{"sheet":"Vendas","col":1,"value":"Monitor"}},False),
("row_not_exists_pos",good,{"type":"row_not_exists","params":{"sheet":"Vendas","col":1,"value":"Monitor"}},True),
("row_count_pos",good,{"type":"row_count","params":{"sheet":"Vendas","expected":4}},True),
("row_matches_pos",good,{"type":"row_matches","params":{"sheet":"Vendas","expected":["Teclado","25"]}},True),
("column_exists_pos",good,{"type":"column_exists","params":{"sheet":"Vendas","col":2}},True),
("column_not_exists_pos",good,{"type":"column_not_exists","params":{"sheet":"Vendas","col":3}},True),
("column_values_pos",good,{"type":"column_values","params":{"sheet":"Vendas","col":1,"expected":["Produto","Teclado","Mouse","Total"]}},True),
("column_order_pos",good,{"type":"column_order","params":{"sheet":"Vendas","expected":["Produto","Quantidade"]}},True),
("sheet_exists_pos",good,{"type":"sheet_exists","params":{"sheet":"Resumo"}},True),
("sheet_exists_neg",bad,{"type":"sheet_exists","params":{"sheet":"Resumo"}},False),
("sheet_not_exists_pos",bad,{"type":"sheet_not_exists","params":{"sheet":"Resumo"}},True),
("sheet_count_pos",good,{"type":"sheet_count","params":{"expected":2}},True),
("sheet_order_pos",good,{"type":"sheet_order","params":{"expected":["Vendas","Resumo"]}},True),
("sheet_renamed_pos",renamed,{"type":"sheet_renamed","params":{"old":"Resumo","new":"ResumoNovo"}},True),
("sheet_renamed_neg",renamed,{"type":"sheet_renamed","params":{"old":"Resumo","new":"ResumoErrado"}},False),
("by_label_pos",good,{"type":"cell_value_by_row_label","params":{"sheet":"Vendas","label_col":1,"label":"Teclado","target_col":2,"expected":"25,0"}},True),
("by_label_neg",bad,{"type":"cell_value_by_row_label","params":{"sheet":"Vendas","label_col":1,"label":"Teclado","target_col":2,"expected":25}},False),
("formula_pos",good,{"type":"formula_in_cell","params":{"sheet":"Vendas","row":4,"col":2,"expected":"=SOMA(B2:B3)"}},True),
("formula_neg",good,{"type":"formula_in_cell","params":{"sheet":"Vendas","row":4,"col":2,"expected":"=MÉDIA(B2:B3)"}},False),
("formula_pattern_pos",good,{"type":"formula_pattern","params":{"sheet":"Vendas","row":4,"col":2,"pattern":"^=SUM\\(B2:B3\\)$"}},True),
("formula_result_pos",good,{"type":"formula_result","params":{"sheet":"Vendas","row":4,"col":2,"expected":35}},True),
("formula_result_neg",bad,{"type":"formula_result","params":{"sheet":"Vendas","row":4,"col":2,"expected":35}},False),
("sorted_asc_pos",asc,{"type":"range_sorted_ascending","params":{"sheet":"Dados","col":1,"start_row":1,"end_row":3}},True),
("sorted_asc_neg",desc,{"type":"range_sorted_ascending","params":{"sheet":"Dados","col":1,"start_row":1,"end_row":3}},False),
("sorted_desc_pos",desc,{"type":"range_sorted_descending","params":{"sheet":"Dados","col":1,"start_row":1,"end_row":3}},True),
("sorted_desc_neg",asc,{"type":"range_sorted_descending","params":{"sheet":"Dados","col":1,"start_row":1,"end_row":3}},False),
("row_inserted_alias",good,{"type":"row_inserted","params":{"sheet":"Vendas","col":1,"value":"Mouse"}},True),
("row_deleted_alias",good,{"type":"row_deleted","params":{"sheet":"Vendas","col":1,"value":"Monitor"}},True),
("column_inserted_alias",good,{"type":"column_inserted","params":{"sheet":"Vendas","col":2}},True),
("column_deleted_alias",good,{"type":"column_deleted","params":{"sheet":"Vendas","col":3}},True),
("range_copied_pos",copied,{"type":"range_copied","params":{"sheet":"Dados","target_row":1,"target_col":3,"rows":2,"cols":2,"expected":[["A","B"],["C","D"]]}},True),
("range_copied_neg",moved,{"type":"range_copied","params":{"sheet":"Dados","target_row":1,"target_col":3,"rows":2,"cols":2,"expected":[["X","B"],["C","D"]]}},False),
("range_moved_pos",moved,{"type":"range_moved","params":{"sheet":"Dados","source_row":1,"source_col":1,"target_row":1,"target_col":3,"rows":2,"cols":2,"expected":[["A","B"],["C","D"]],"source_cleared":True}},True),
("filter_active_pos",filtered,{"type":"filter_active","params":{}},True),
("filter_active_neg",good,{"type":"filter_active","params":{}},False),
("filter_condition_pos",filtered,{"type":"filter_condition","params":{"field_number":1,"operator":"=","value":"A"}},True),
("filter_condition_neg",filtered,{"type":"filter_condition","params":{"field_number":1,"operator":"=","value":"B"}},False),
("visible_rows_match_pos",filtered,{"type":"visible_rows_match","params":{"sheet":"Vendas","field_number":1,"operator":"=","value":"A","key_col":1,"expected_keys":["Teclado","Monitor"]}},True),
]
passed=false_pos=false_neg=0
for name,path,spec,expected in cases:
    try: got=verify(path,spec)
    except Exception as e:
        got=f"EXCEPTION:{type(e).__name__}:{e}"
    ok=(got==expected); passed+=int(ok)
    false_pos+=int(got is True and expected is False); false_neg+=int(got is False and expected is True)
    print(f"{name}: EXPECTED={expected} GOT={got} {'PASS' if ok else 'FAIL'}")
fp=normalize_formula("=SOMA(B2:B3)")==normalize_formula("of:=SUM([.B2:.B3])")
np=normalize_number("2,5")==2.5
print(f"NORMALIZE_PTBR_FORMULA={'PASS' if fp else 'FAIL'}")
print(f"NORMALIZE_PTBR_NUMBER={'PASS' if np else 'FAIL'}")
print(f"VERIFIER_CASES={passed}/{len(cases)}")
print(f"FALSE_POSITIVES={false_pos}")
print(f"FALSE_NEGATIVES={false_neg}")
ok=passed==len(cases) and fp and np and false_pos==0 and false_neg==0
print("STAGE2_VERIFIER_GATE=PASS" if ok else "STAGE2_VERIFIER_GATE=FAIL")
sys.exit(0 if ok else 1)
