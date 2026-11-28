"""Kiểm nhập bộ đề: cd ailab && python3 -m unittest test_importer"""
import base64
import io
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("AILAB_DB", os.path.join(tempfile.mkdtemp(), "i.db"))

import importer  # noqa: E402
import store  # noqa: E402


def make_xlsx(rows):
    ss, body = [], []
    for r, row in enumerate(rows, 1):
        cs = []
        for c, v in enumerate(row):
            ref = "ABCDEFGH"[c] + str(r)
            if v is None:
                continue
            if isinstance(v, (int, float)):
                cs.append('<c r="%s"><v>%s</v></c>' % (ref, v))
            else:
                ss.append(v)
                cs.append('<c r="%s" t="s"><v>%d</v></c>' % (ref, len(ss) - 1))
        body.append('<row r="%d">%s</row>' % (r, "".join(cs)))
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", '<worksheet %s><sheetData>%s</sheetData></worksheet>' % (ns, "".join(body)))
        z.writestr("xl/sharedStrings.xml", '<sst %s>%s</sst>' % (ns, "".join("<si><t>%s</t></si>" % s.replace("&", "&amp;") for s in ss)))
    return b.getvalue()


def b64(b):
    return base64.b64encode(b).decode()


class Import(unittest.TestCase):
    def check(self, content):  # mọi dòng sinh ra phải qua bộ phân tích thật của server
        return len(store.parse_questions(content))

    def test_xlsx_with_header(self):
        x = make_xlsx([["Câu hỏi", "A", "B", "C", "D", "Đáp án"], ["2+2=?", "3", "4", "5", None, "B"], ["Trái đất tròn", None, None, None, None, "Đúng"],
                       ["Thủ đô VN?", "Huế", "Hà Nội", None, None, "Hà Nội"], ["Lỗi", "x", "y", None, None, "Z"]])
        r = importer.run({"filename": "de.xlsx", "data": b64(x)})
        self.assertEqual(r["count"], 3)
        self.assertEqual(r["content"].splitlines(), ["2+2=? | 3 | 4 | 5 | =B", "Trái đất tròn | =Đúng", "Thủ đô VN? | Huế | Hà Nội | =B"])
        self.assertEqual(r["errors"][0]["line"], 5)
        self.assertEqual(self.check(r["content"]), 3)

    def test_xlsx_no_header_with_stt_and_numbers(self):
        x = make_xlsx([[1, "1+1?", "1", "2", 2]])
        r = importer.run({"filename": "a.xlsx", "data": b64(x)})
        self.assertEqual(r["content"], "1+1? | 1 | 2 | =B")

    def test_csv_semicolon_bom(self):
        t = b"\xef\xbb\xbf" + "Câu hỏi;A;B;Đáp án\nMàu trời?;Xanh;Đỏ;A\n".encode("utf-8")
        r = importer.run({"filename": "a.csv", "data": b64(t)})
        self.assertEqual(r["content"], "Màu trời? | Xanh | Đỏ | =A")

    def test_natural_text(self):
        t = "Câu 1: Thủ đô của Việt Nam là gì?\nA. Huế\n*B. Hà Nội\nC. Đà Nẵng\n\n2. Mặt trời mọc ở hướng nào?\nA) Đông\nB) Tây\nĐáp án: A\n\n3. Trái đất tròn.\nĐáp án: Đúng\n\n4. Câu thiếu đáp án\nA. x\nB. y\n"
        r = importer.run({"text": t})
        self.assertEqual(r["content"].splitlines(), ["Thủ đô của Việt Nam là gì? | Huế | Hà Nội | Đà Nẵng | =B", "Mặt trời mọc ở hướng nào? | Đông | Tây | =A", "Trái đất tròn. | =Đúng"])
        self.assertEqual(r["error_count"], 1)
        self.assertEqual(self.check(r["content"]), 3)

    def test_pipe_text_passthrough_and_errors(self):
        r = importer.run({"text": "Q1 | a | b | =b\nhỏng dòng\n"})
        self.assertEqual((r["count"], r["error_count"]), (1, 1))

    def test_bad_files(self):
        for d in ({"filename": "a.xls", "data": b64(b"\xd0\xcf\x11\xe0")}, {"filename": "a.xlsx", "data": b64(b"PKxxxx")}, {}):
            with self.assertRaises(store.Err):
                importer.run(d)
        evil = io.BytesIO()
        with zipfile.ZipFile(evil, "w") as z:
            z.writestr("xl/worksheets/sheet1.xml", '<!DOCTYPE x [<!ENTITY a "b">]><worksheet/>')
        with self.assertRaises(store.Err):
            importer.run({"filename": "e.xlsx", "data": b64(evil.getvalue())})


if __name__ == "__main__":
    unittest.main()
