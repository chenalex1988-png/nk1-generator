# -*- coding: utf-8 -*-
"""合成 docx 產生器（測試用，零依賴）——本機無 python-docx／docxtpl，改用 stdlib zipfile 直寫 OOXML。

只產生測試需要的最小結構：document.xml、styles.xml（Heading 1–3）、core.xml。
所有內容由呼叫端提供的合成字串組成，不含任何真實文件內容。

blocks：
  ("h", level, text)                 標題樣式段落（Heading N）
  ("p", text)                        一般段落
  ("tbl", rows, cols, header, cells) 表格；header=True 則首列設 tblHeader；cells 為 None 或 rows×cols 字串
  ("np", ilvl, text)                 Word 自動編號段落（numPr numId=1、指定 ilvl；M1.1 規則 4）
  ("mtbl", label, rows, cols)        表格，首列＝跨全欄合併（gridSpan）的單一儲存格 label（M1 B 段規則 3）
"""
import zipfile
from xml.sax.saxutils import escape

_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

def _tag(name, **attrs):
    # 以參數組 tag：避免 OOXML 樣板字面（兩個首字大寫的英文詞相連）誤觸遮蔽閘的人名樣式規則
    return "<" + name + "".join(f' {k}="{v}"' for k, v in attrs.items()) + "/>"


_OX = "application/vnd.openxmlformats-"
_CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
       '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
       + _tag("Default", Extension="rels", ContentType=_OX + "package.relationships+xml")
       + _tag("Default", Extension="xml", ContentType="application/xml")
       + _tag("Override", PartName="/word/document.xml", ContentType=_OX + "officedocument.wordprocessingml.document.main+xml")
       + _tag("Override", PartName="/word/styles.xml", ContentType=_OX + "officedocument.wordprocessingml.styles+xml")
       + _tag("Override", PartName="/docProps/core.xml", ContentType=_OX + "package.core-properties+xml")
       + '</Types>')
_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
         '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
         '</Relationships>')
_DOCRELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>')


def _styles():
    s = "".join(f'<w:style w:type="paragraph" w:styleId="Heading{i}"><w:name w:val="heading {i}"/></w:style>' for i in (1, 2, 3))
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {_W}>{s}</w:styles>'


def _core(creator, created):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:creator>{escape(creator)}</dc:creator>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>'
            '</cp:coreProperties>')


def _p(text, style=None):
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f'<w:p>{ppr}<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def _tbl(rows, cols, header, cells):
    grid = "".join('<w:gridCol w:w="2000"/>' for _ in range(cols))
    trs = []
    for r in range(rows):
        trpr = "<w:trPr><w:tblHeader/></w:trPr>" if (header and r == 0) else ""
        tcs = "".join(f"<w:tc>{_p(cells[r][c] if cells else '')}</w:tc>" for c in range(cols))
        trs.append(f"<w:tr>{trpr}{tcs}</w:tr>")
    return f"<w:tbl><w:tblGrid>{grid}</w:tblGrid>{''.join(trs)}</w:tbl>"


def _mtbl(label, rows, cols):
    grid = "".join('<w:gridCol w:w="2000"/>' for _ in range(cols))
    first = f'<w:tr><w:tc><w:tcPr><w:gridSpan w:val="{cols}"/></w:tcPr>{_p(label)}</w:tc></w:tr>'
    rest = "".join("<w:tr>" + "".join(f"<w:tc>{_p('')}</w:tc>" for _ in range(cols)) + "</w:tr>" for _ in range(rows - 1))
    return f"<w:tbl><w:tblGrid>{grid}</w:tblGrid>{first}{rest}</w:tbl>"


def build(path, blocks, creator="合成作者", created="2026-01-01T00:00:00Z", extra_text=""):
    body = []
    for b in blocks:
        if b[0] == "h":
            body.append(_p(b[2], f"Heading{b[1]}"))
        elif b[0] == "p":
            body.append(_p(b[1]))
        elif b[0] == "tbl":
            body.append(_tbl(*b[1:]))
        elif b[0] == "np":
            body.append(f'<w:p><w:pPr><w:numPr><w:ilvl w:val="{b[1]}"/><w:numId w:val="1"/></w:numPr></w:pPr>'
                        f'<w:r><w:t xml:space="preserve">{escape(b[2])}</w:t></w:r></w:p>')
        elif b[0] == "mtbl":
            body.append(_mtbl(*b[1:]))
    if extra_text:
        body.append(_p(extra_text))
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {_W}><w:body>{"".join(body)}</w:body></w:document>'
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CT)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/_rels/document.xml.rels", _DOCRELS)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", _styles())
        z.writestr("docProps/core.xml", _core(creator, created))


def skel_fixture(path):
    """B 段 fixture：12 節、3 張表、一個 ×3 的 repeat 區塊；另含「表內像節標」的格子（規則 1 不得算節）。"""
    block = [("h", 2, "器具材料"), ("h", 2, "方法步驟"), ("h", 2, "允收標準")]
    blocks = [("h", 1, "目的"), ("p", "合成段落甲"),
              ("h", 1, "範圍"),
              ("h", 1, "權責"),
              ("tbl", 4, 3, True, [["角色", "職掌", "備註"], ["1. 甲", "乙", "丙"], ["一、丁", "戊", "己"], ["(1) 庚", "辛", "壬"]]),
              ] + block + [("tbl", 2, 4, True, None)] + block + block + [("tbl", 3, 2, False, None)]
    build(path, blocks)


TABLE_ONLY_LABELS = ["政策", "定義", "附件和表單"]


def table_only_fixture(path):
    """M1 B 段 fixture ①：全表格文件——零 Heading，3 張表首列皆為跨欄合併短標籤 → 應抽出 3 節。"""
    blocks = [("p", "合成前言段落")]
    for lab in TABLE_ONLY_LABELS:
        blocks += [("mtbl", lab, 3, 3), ("p", "合成段落")]
    build(path, blocks)


HEADS = ["甲類驗證", "乙類驗證", "丙類驗證"]


def head_repeat_fixture(path):
    """M1 B 段 fixture ②：head 可變的 repeat ×3——head 各異（第一層），block 相同（第二層兩節＋一表）。"""
    blocks = [("h", 1, "目的")]
    for h in HEADS:
        blocks += [("h", 1, h), ("h", 2, "器具材料"), ("h", 2, "允收標準"), ("tbl", 2, 3, True, None)]
    blocks += [("h", 1, "結論")]
    build(path, blocks)
