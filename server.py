from uuid import uuid4
import sys
from flask import Flask, jsonify, request, render_template
import ast

from pdfminer.pdfparser import PDFParser #,PDFNoOutlines
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfdevice import PDFDevice
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.layout import LAParams ,LTTextBox, LTTextLine, LTFigure, LTImage ,LTTextLineHorizontal, LTChar, LTText
from pdfminer.converter import PDFPageAggregator
import math
import os   # cái này dùng để duyệt file , tìm đường dẫn thư mục

# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-','')

@app.route('/', methods=['POST'])	
def get_coordinates():
    filename = request.json.get('fileName')	
    x = request.json.get('x')	
    y = request.json.get('y')	
    width = request.json.get('width')	
    height = request.json.get('height')	
    numberpage = request.json.get('numberpage')	

    response = {
        'fileName': filename,
        'x': x,
        'y': y,
        'width': width,
        'height': height,
        'numberpage' : numberpage,
        'data': extract_text_box(filename, x, y, width, height, numberpage)
    }
    return jsonify(response), 201

def extract_text_box(fileName, x, y, weiht, height, numberpage):
    # tạo đối tượng lưu trữ các tài nguyên của trang pdf
    rsrcmgr = PDFResourceManager()
    # tạo đối tượng chứa các thông số mặc định cho phân tích layout
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    # mở file
    fp = open(fileName, 'rb')
    # tạo một đối tượng phân tích cú pháp liên kết với đối tượng tệp pdf
    parser = PDFParser(fp)
    # tạo một đối tượng PDFDocument lưu trữ cấu trúc tài liệu
    doc = PDFDocument(parser)
    parsed = []
    font=[]
    for i,page in enumerate(PDFPage.create_pages(doc)):
        if (i == numberpage):
            # đưa page pdf vào trình thông dịch xử lý
            interpreter.process_page(page)

            # receive the LTPage object for this page
            layout = device.get_result()
            for Obj in layout._objs:
                if isinstance(Obj, LTTextBox):
                    parsed.append(go_textbox(Obj, x, y, weiht, height))
                elif isinstance(Obj, LTFigure):
                    parsed.append(go_figure(Obj, x, y, weiht, height))                   
    return parsed

def go_textbox(Objs, x, y, weiht, height):
    parsed = []
    for line in Objs._objs:
        if len(parsed) >= 1:
            parsed[-1]['text'] += ' '
        # Tất cả những đoạn text liền nhau sẽ được đưa vào cùng 1 mảng
        for char in line._objs:
            if isinstance(char, LTChar) and (x < char.x0 and y < char.y0 and (x+weiht) > char.x1 and (y+height) > char.y1):
                if len(parsed) >= 1 and char.fontname == parsed[-1]['font']:
                    parsed[-1]['text'] += str(char.get_text())
                else: 
                    parsed.append({'text': char.get_text(),'font': char.fontname})
    return parsed

def go_figure(Objs, x, y, weiht, height):
    parsed = []
    for Obj in Objs:
        if isinstance(Obj, LTFigure):
            p = go_figure(Obj, x, y, weiht, height)
            if len(p) > 0: parsed.append(p)
        elif isinstance(Obj, LTTextBox):
            parsed.append(go_textbox(Obj, x, y, weiht, height))
        elif isinstance(Obj, LTChar) :
            char = Obj
            if x < char.x0 and y < char.y0 and (x+weiht) > char.x1 and (y+height) > char.y1:
                if len(parsed) >= 1 and char.fontname == parsed[-1]['font']:
                    parsed[-1]['text'] += str(char.get_text())
                else : 
                    parsed.append({'text': char.get_text(),'font': char.fontname})
    return parsed


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port listening')
    args = parser.parse_args()
    port = args.port
    app.debug = True
    app.run(host='0.0.0.0', port=port)
