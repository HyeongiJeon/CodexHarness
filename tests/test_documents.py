import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from harness.documents import iter_segments


def pdf_bytes(text='Synthetic PDF text', empty=False):
    stream = '' if empty else f'BT /F1 12 Tf 50 700 Td ({text}) Tj ET'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
               f'<< /Length {len(stream)} >>\nstream\n{stream}\nendstream'.encode(), b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    data, offsets = b'%PDF-1.4\n', [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data)); data += f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n'
    start = len(data)
    data += f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode()
    for offset in offsets[1:]: data += f'{offset:010d} 00000 n \n'.encode()
    return data + f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_text_encoding_locations_and_caps(self):
        p = self.root/'a.md'; p.write_text('# Header\n서울\nEND\n', encoding='utf-16')
        records = list(iter_segments(p))
        self.assertEqual(records[-1]['locator']['line'], 3)
        self.assertEqual(records[1]['locator']['section'], 'Header')
        capped = list(iter_segments(p, max_chars=10))
        self.assertTrue(any(r['extraction_status'] == 'partial' for r in capped))
        self.assertLessEqual(sum(len(r['text']) for r in capped), 10)

    def test_csv_multiline_and_json_pointers(self):
        p = self.root/'a.csv'; p.write_text('id,text\n1,"first\nlast"\n', encoding='utf-8')
        records = list(iter_segments(p))
        self.assertEqual(records[1]['locator']['row'], 2)
        self.assertEqual(records[1]['locator']['line_end'], 3)
        self.assertEqual(json.loads(records[1]['text']), ['1','first\nlast'])
        p = self.root/'a.jsonl'; p.write_text('{"rows":[{"name":"서울"}]}\n')
        record = list(iter_segments(p))[0]
        self.assertEqual(record['locator']['pointer'], '/rows/0/name')
        self.assertIn('서울', record['text'])
        p=self.root/'exact.json';p.write_text('{"amount":9007199254740992.1}')
        self.assertIn('9007199254740992.1',list(iter_segments(p))[0]['text'])

    def test_docx_paragraph_and_table_cell(self):
        p = self.root/'a.docx'
        with zipfile.ZipFile(p,'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>Intro</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Cell42</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
        records = [r for r in iter_segments(p) if r['text']]
        self.assertEqual(records[1]['text'],'Cell42')
        self.assertEqual(records[1]['locator']['cell'],1)
        self.assertEqual(records[1]['locator']['table'],1)
        with zipfile.ZipFile(p,'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="urn:w"><w:body/></w:document>')
        self.assertTrue(any(r['extraction_status']=='partial' for r in iter_segments(p)))

    def test_xlsx_inline_cell_formula_and_locator(self):
        p = self.root/'a.xlsx'; ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        with zipfile.ZipFile(p,'w') as z:
            z.writestr('xl/workbook.xml',f'<workbook xmlns="{ns}" xmlns:r="urn:r"><sheets><sheet name="Data" sheetId="1" r:id="r1"/></sheets></workbook>')
            z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>')
            z.writestr('xl/worksheets/sheet1.xml',f'<worksheet xmlns="{ns}"><sheetData><row r="8"><c r="A8" t="inlineStr"><is><t>Marker</t></is></c><c r="B8"><f>1+1</f><v>2</v></c><c r="C8"><f>2+2</f></c></row></sheetData></worksheet>')
        records = list(iter_segments(p))
        self.assertEqual(records[0]['locator'], {'format':'xlsx','sheet':'Data','row':8,'cell':'A8','part':1,'char_start':0,'char_end':6})
        self.assertIn('cached', ' '.join(records[1]['limitations']))
        self.assertEqual(records[2]['extraction_status'],'partial')

    @unittest.skipUnless(shutil.which('pdftotext'),'pdftotext unavailable')
    def test_real_pdf_and_image_only_explicit_failure(self):
        p = self.root/'a.pdf'; p.write_bytes(pdf_bytes())
        records = list(iter_segments(p)); self.assertIn('Synthetic PDF text',''.join(r['text'] for r in records))
        self.assertEqual(records[0]['locator']['page'],1)
        self.assertIn('tables',' '.join(records[0]['limitations']))
        p.write_bytes(pdf_bytes(empty=True))
        self.assertEqual(list(iter_segments(p))[0]['extraction_status'],'unsupported')

    def test_unavailable_invalid_and_oversized_json_are_not_success(self):
        p=self.root/'a.hwp';p.write_bytes(b'opaque')
        self.assertEqual(list(iter_segments(p))[0]['extraction_status'],'unsupported')
        p=self.root/'bad.docx';p.write_bytes(b'not zip')
        self.assertEqual(list(iter_segments(p))[0]['extraction_status'],'error')
        p=self.root/'large.json';p.write_text(' ' * 66000)
        self.assertEqual(list(iter_segments(p,max_chars=20))[0]['extraction_status'],'partial')
