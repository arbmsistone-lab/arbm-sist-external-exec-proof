from pathlib import Path
from shutil import copy2
import zipfile, tempfile, os
from odf.opendocument import OpenDocumentSpreadsheet, load
from odf.table import Table,TableRow,TableCell
from odf.text import P

OUT=Path(__file__).parent/"fixtures"; OUT.mkdir(exist_ok=True)

def txt(v):
    c=TableCell(valuetype="string"); c.addElement(P(text=str(v))); return c
def num(v):
    c=TableCell(valuetype="float",value=str(v)); c.addElement(P(text=str(v))); return c
def formula(f,res):
    c=TableCell(valuetype="float",value=str(res),formula=f); c.addElement(P(text=str(res))); return c
def row(*vals):
    r=TableRow()
    for v in vals:
        if isinstance(v,tuple) and v[0]=="F": r.addElement(formula(v[1],v[2]))
        elif isinstance(v,(int,float)): r.addElement(num(v))
        else: r.addElement(txt(v))
    return r

def save(path,rows,sheets=("Vendas",)):
    d=OpenDocumentSpreadsheet()
    for i,name in enumerate(sheets):
        s=Table(name=name)
        if i==0:
            for rr in rows:s.addElement(row(*rr))
        d.spreadsheet.addElement(s)
    d.save(str(path),addsuffix=False)

base_rows=[
    ("Produto","Quantidade"),
    ("Teclado",10),
    ("Mouse",5),
    ("Total",("F","of:=SUM([.B2:.B3])",15)),
]
save(OUT/"original.ods",base_rows,("Vendas","Resumo"))

# legal cell edit
r=[list(x) for x in base_rows]; r[1][1]=12; save(OUT/"expected_cell.ods",r,("Vendas","Resumo")); copy2(OUT/"expected_cell.ods",OUT/"final_cell_ok.ods")
# side effect: target right but Mouse changed too
r2=[list(x) for x in r]; r2[2][1]=99; save(OUT/"final_side_cell.ods",r2,("Vendas","Resumo"))
# sheet deleted
save(OUT/"final_sheet_deleted.ods",r,("Vendas",))
# extra row
r3=[list(x) for x in r]+[["Extra",1]]; save(OUT/"final_extra_row.ods",r3,("Vendas","Resumo"))
# formula lost
r4=[list(x) for x in r]; r4[3][1]=17; save(OUT/"final_formula_lost.ods",r4,("Vendas","Resumo"))

# sort legal
sorted_rows=[base_rows[0],base_rows[2],base_rows[1],base_rows[3]]
save(OUT/"expected_sort.ods",sorted_rows,("Vendas","Resumo")); copy2(OUT/"expected_sort.ods",OUT/"final_sort_ok.ods")
# insert legal
insert_rows=[base_rows[0],base_rows[1],("Monitor",7),base_rows[2],base_rows[3]]
save(OUT/"expected_insert.ods",insert_rows,("Vendas","Resumo")); copy2(OUT/"expected_insert.ods",OUT/"final_insert_ok.ods")
# delete legal
delete_rows=[base_rows[0],base_rows[2],base_rows[3]]
save(OUT/"expected_delete.ods",delete_rows,("Vendas","Resumo")); copy2(OUT/"expected_delete.ods",OUT/"final_delete_ok.ods")
# copy legal
copy_rows=[("A","B","A","B"),("C","D","C","D")]
save(OUT/"expected_copy.ods",copy_rows,("Dados",)); copy2(OUT/"expected_copy.ods",OUT/"final_copy_ok.ods")
# move legal
move_rows=[("","","A","B"),("","","C","D")]
save(OUT/"expected_move.ods",move_rows,("Dados",)); copy2(OUT/"expected_move.ods",OUT/"final_move_ok.ods")

# metadata-only: copy expected cell and rewrite meta.xml if present
src=OUT/"expected_cell.ods"; dst=OUT/"final_metadata_only.ods"; copy2(src,dst)
with zipfile.ZipFile(dst,"r") as zin:
    entries={n:zin.read(n) for n in zin.namelist()}
if "meta.xml" in entries:
    entries["meta.xml"]=entries["meta.xml"].replace(b"</office:meta>",b"<meta:user-defined meta:name='noise'>changed</meta:user-defined></office:meta>")
    tmp=dst.with_suffix(".tmp")
    with zipfile.ZipFile(tmp,"w") as zout:
        for n,data in entries.items():
            comp=zipfile.ZIP_STORED if n=="mimetype" else zipfile.ZIP_DEFLATED
            zout.writestr(n,data,compress_type=comp)
    os.replace(tmp,dst)

# invalid format masquerading as ods
(OUT/"invalid_format.ods").write_text("not an ods",encoding="utf-8")
# metadata/view/cursor noise using a real LibreOffice-produced ODS
real_src=Path(__file__).parent.parent/"fixtures"/"development"/"m1_reset_fixture.ods"
meta_expected=OUT/"meta_expected.ods"; meta_noisy=OUT/"meta_noisy.ods"
copy2(real_src,meta_expected); copy2(real_src,meta_noisy)
with zipfile.ZipFile(meta_noisy,"r") as zin:
    entries={n:zin.read(n) for n in zin.namelist()}
meta=entries["meta.xml"].decode("utf-8")
meta=meta.replace("<office:meta>","<office:meta><dc:creator>Noise Author</dc:creator><dc:date>2099-12-31T23:59:59</dc:date><meta:initial-creator>Noise Initial</meta:initial-creator>")
entries["meta.xml"]=meta.encode("utf-8")
settings=entries["settings.xml"].decode("utf-8")
settings=settings.replace('<config:config-item config:name="VisibleAreaTop" config:type="int">0</config:config-item>','<config:config-item config:name="VisibleAreaTop" config:type="int">999</config:config-item>')
settings=settings.replace('<config:config-item config:name="VisibleAreaLeft" config:type="int">0</config:config-item>','<config:config-item config:name="VisibleAreaLeft" config:type="int">777</config:config-item>')
settings=settings.replace('</config:config-item-set><config:config-item-set config:name="ooo:configuration-settings">','<config:config-item config:name="CursorPositionX" config:type="int">4</config:config-item><config:config-item config:name="CursorPositionY" config:type="int">8</config:config-item></config:config-item-set><config:config-item-set config:name="ooo:configuration-settings">',1)
entries["settings.xml"]=settings.encode("utf-8")
tmp=meta_noisy.with_suffix(".rewrite")
with zipfile.ZipFile(tmp,"w") as zout:
    for n,data in entries.items():
        comp=zipfile.ZIP_STORED if n=="mimetype" else zipfile.ZIP_DEFLATED
        zout.writestr(n,data,compress_type=comp)
os.replace(tmp,meta_noisy)
print("STAGE3_FIXTURES_BUILT")
