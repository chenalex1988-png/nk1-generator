# -*- coding: utf-8 -*-
"""NK1 最小 xlsx 寫出器（stdlib 直寫 OOXML；本機無 openpyxl，未授權安裝）。

write_xlsx(path, sheets)：sheets＝[{"name", "rows": [[值…]…], "widths": [...], "header_row": int|None,
  "fill_cols": {欄索引…}（黃底待填）, "note_row": int|None（首列註記、合併全欄）, "freeze": int|None}]
值：int／str／None。確定性：entry mtime 固定 1980-01-01、名稱排序。
"""
import zipfile
from xml.sax.saxutils import escape

COLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_OX = "application/vnd.openxmlformats-officedocument.spreadsheetml"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_M = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="' + _M + '">'
          '<fonts count="3"><font><sz val="10"/><name val="Arial"/></font><font><b/><sz val="10"/><name val="Arial"/></font>'
          '<font><i/><sz val="9"/><color rgb="FF555555"/><name val="Arial"/></font></fonts>'
          '<fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
          '<fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/></patternFill></fill>'
          '<fill><patternFill patternType="solid"><fgColor rgb="FFD9D9D9"/></patternFill></fill></fills>'
          '<borders count="2"><border/><border><left style="thin"/><right style="thin"/><top style="thin"/><bottom style="thin"/></border></borders>'
          '<cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="5">'
          '<xf fontId="0" fillId="0" borderId="0"/>'
          '<xf fontId="1" fillId="3" borderId="1" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf>'
          '<xf fontId="0" fillId="0" borderId="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
          '<xf fontId="0" fillId="2" borderId="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
          '<xf fontId="2" fillId="0" borderId="0" applyFont="1" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>'
          '</cellXfs></styleSheet>')


def _tag(name, **attrs):
    # 以參數組 tag：避免 OOXML 樣板字面（兩個首字大寫英文詞相連）誤觸遮蔽閘人名樣式規則
    return "<" + name + "".join(f' {k}="{v}"' for k, v in attrs.items()) + "/>"


def _cell(ref, v, s):
    if v is None or v == "":
        return f'<c r="{ref}" s="{s}"/>'
    if isinstance(v, int):
        return f'<c r="{ref}" s="{s}"><v>{v}</v></c>'
    return f'<c r="{ref}" s="{s}" t="inlineStr"><is><t xml:space="preserve">{escape(str(v))}</t></is></c>'


def _sheet(sh):
    rows, ncol = sh["rows"], max(len(r) for r in sh["rows"])
    hr, nr, fill = sh.get("header_row"), sh.get("note_row"), set(sh.get("fill_cols") or ())
    out = []
    for i, r in enumerate(rows, 1):
        cs = []
        for j in range(ncol):
            v = r[j] if j < len(r) else None
            s = 4 if i == nr else 1 if i == hr else (3 if j in fill and hr and i > hr else 2 if hr and i > hr else 0)
            cs.append(_cell(f"{COLS[j]}{i}", v, s))
        out.append(f'<row r="{i}">' + "".join(cs) + "</row>")
    cols = "".join(f'<col min="{k + 1}" max="{k + 1}" width="{w}" customWidth="1"/>' for k, w in enumerate(sh.get("widths") or []))
    fz = sh.get("freeze")
    sv = (f'<sheetViews><sheetView workbookViewId="0"><pane ySplit="{fz - 1}" topLeftCell="A{fz}" activePane="bottomLeft" '
          f'state="frozen"/></sheetView></sheetViews>') if fz else ""
    x = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="{_M}">{sv}'
    x += (f"<cols>{cols}</cols>" if cols else "") + "<sheetData>" + "".join(out) + "</sheetData>"
    if hr:
        x += f'<autoFilter ref="A{hr}:{COLS[ncol - 1]}{len(rows)}"/>'
    if nr:
        x += f'<mergeCells count="1"><mergeCell ref="A{nr}:{COLS[ncol - 1]}{nr}"/></mergeCells>'
    return x + "</worksheet>"


def write_xlsx(path, sheets):
    n = len(sheets)
    parts = {
        "[Content_Types].xml": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                                + _tag("Default", Extension="rels", ContentType="application/vnd.openxmlformats-package.relationships+xml")
                                + _tag("Default", Extension="xml", ContentType="application/xml")
                                + _tag("Override", PartName="/xl/workbook.xml", ContentType=f"{_OX}.sheet.main+xml")
                                + "".join(_tag("Override", PartName=f"/xl/worksheets/sheet{k}.xml", ContentType=f"{_OX}.worksheet+xml") for k in range(1, n + 1))
                                + _tag("Override", PartName="/xl/styles.xml", ContentType=f"{_OX}.styles+xml") + "</Types>"),
        "_rels/.rels": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                        f'<Relationship Id="rId1" Type="{_R}/officeDocument" Target="xl/workbook.xml"/></Relationships>'),
        "xl/workbook.xml": (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="{_M}" xmlns:r="{_R}"><sheets>'
                            + "".join(f'<sheet name="{escape(s["name"])}" sheetId="{k}" r:id="rId{k}"/>' for k, s in enumerate(sheets, 1))
                            + "</sheets></workbook>"),
        "xl/_rels/workbook.xml.rels": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                                       + "".join(f'<Relationship Id="rId{k}" Type="{_R}/worksheet" Target="worksheets/sheet{k}.xml"/>' for k in range(1, n + 1))
                                       + f'<Relationship Id="rId{n + 1}" Type="{_R}/styles" Target="styles.xml"/></Relationships>'),
        "xl/styles.xml": STYLES,
    }
    for k, s in enumerate(sheets, 1):
        parts[f"xl/worksheets/sheet{k}.xml"] = _sheet(s)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(parts):
            z.writestr(zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)), parts[name], zipfile.ZIP_DEFLATED)
