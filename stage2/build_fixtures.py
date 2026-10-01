from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table,TableRow,TableCell,DatabaseRanges,DatabaseRange,Filter,FilterCondition
from odf.text import P
from pathlib import Path
OUT=Path(__file__).parent/"fixtures"; OUT.mkdir(exist_ok=True)
def txt(v):
    c=TableCell(valuetype="string"); c.addElement(P(text=v)); return c
def num(v):
    c=TableCell(valuetype="float",value=str(v)); c.addElement(P(text=str(v))); return c
def blank():
    return TableCell()
def formula(f,res):
    c=TableCell(valuetype="float",value=str(res),formula=f); c.addElement(P(text=str(res))); return c
def row(*vals):
    r=TableRow()
    for v in vals:
        if v is None:r.addElement(blank())
        else:r.addElement(num(v) if isinstance(v,(int,float)) else txt(v))
    return r
def make_main(path,q,include_summary):
    d=OpenDocumentSpreadsheet(); s=Table(name="Vendas")
    s.addElement(row("Produto","Quantidade")); s.addElement(row("Teclado",q)); s.addElement(row("Mouse",10))
    r=TableRow(); r.addElement(txt("Total")); r.addElement(formula("of:=SUM([.B2:.B3])",q+10)); s.addElement(r)
    d.spreadsheet.addElement(s)
    if include_summary:d.spreadsheet.addElement(Table(name="Resumo"))
    d.save(str(path),addsuffix=False)
def make_sorted(path,descending=False):
    d=OpenDocumentSpreadsheet(); s=Table(name="Dados")
    for v in ([1,2,3] if not descending else [3,2,1]):s.addElement(row(v))
    d.spreadsheet.addElement(s); d.save(str(path),addsuffix=False)
def make_renamed(path):
    d=OpenDocumentSpreadsheet(); d.spreadsheet.addElement(Table(name="ResumoNovo")); d.save(str(path),addsuffix=False)
def make_ranges(path,moved=False):
    d=OpenDocumentSpreadsheet(); s=Table(name="Dados")
    if moved:
        s.addElement(row(None,None,"A","B")); s.addElement(row(None,None,"C","D"))
    else:
        s.addElement(row("A","B","A","B")); s.addElement(row("C","D","C","D"))
    d.spreadsheet.addElement(s); d.save(str(path),addsuffix=False)
def make_filter(path):
    d=OpenDocumentSpreadsheet(); s=Table(name="Vendas")
    s.addElement(row("Produto","Categoria")); s.addElement(row("Teclado","A")); s.addElement(row("Mouse","B")); s.addElement(row("Monitor","A"))
    d.spreadsheet.addElement(s)
    drs=DatabaseRanges(); dr=DatabaseRange(name="FiltroVendas",targetrangeaddress="Vendas.A1:B4",containsheader="true",displayfilterbuttons="true")
    f=Filter(); f.addElement(FilterCondition(fieldnumber="1",operator="=",value="A")); dr.addElement(f); drs.addElement(dr); d.spreadsheet.addElement(drs)
    d.save(str(path),addsuffix=False)
make_main(OUT/"good.ods",25,True); make_main(OUT/"bad.ods",24,False)
make_sorted(OUT/"sorted_asc.ods",False); make_sorted(OUT/"sorted_desc.ods",True)
make_renamed(OUT/"renamed.ods"); make_ranges(OUT/"copied.ods",False); make_ranges(OUT/"moved.ods",True); make_filter(OUT/"filtered.ods")
print("FIXTURES_BUILT")
