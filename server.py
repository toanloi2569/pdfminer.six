from pdfminer import utils
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage, PDFTextExtractionNotAllowed
from pdfminer.pdfdevice import PDFDevice, TagExtractor
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFLayoutAnalyzer, PDFConverter, XMLConverter, PDFPageAggregator
from pdfminer.image import ImageWriter
from pdfminer.cmapdb import CMapDB
from pdfminer.pdfdevice import PDFTextDevice
from pdfminer.pdffont import PDFUnicodeNotDefined
from pdfminer.layout import LAParams, LTContainer, LTPage, LTText, LTLine, LTRect, LTCurve, LTFigure, LTImage, LTChar, LTTextLine, LTTextBox, LTTextBoxVertical, LTTextGroup
from pdfminer.utils import apply_matrix_pt, mult_matrix, enc, bbox2str

from flask import Flask, jsonify, request, render_template
from lxml import etree
import wget
import os
from os.path import join
import io
import re
import requests
from Anno import Anno

app = Flask(__name__)

pg = None
root = None
annos = []
tree = None


@app.route('/', methods=['GET', 'POST'])
def run():
    datas = request.get_json()
    init(datas[0]['documentId'])
    for data in datas:
        annolist = data['annotations']
        page = data['pageNumber']

        for anno in annolist:
            if anno['type'] == "area":
                anno['page'] = page
                add_anno(anno)
            elif anno['type'] == "highlight":
                for reltangle in anno['rectangles']:
                    n_anno = anno
                    n_anno.update(reltangle)
                    anno['page'] = page
                    add_anno(n_anno)

    finish(datas[0]['documentId'])
    return "ok", 200

# @app.route('/init', methods=['POST'])
def init(url):
    global pg, root, tree

    r = requests.get(url, verify=False)
    with open('pdf-file/tmp.pdf', 'wb') as f:
        f.write(r.content)

    inf = open('pdf-file/tmp.pdf', 'rb')
    outf = open('pdf-file/tmp.xml', 'wb')
    pg = convert_xml(inf, outf)
    inf.close()
    outf.close()

    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse("pdf-file/tmp.xml", parser)
    root = tree.getroot()
    root = clear_xml(root)


# @app.route('/add_anno', methods=['POST'])
def add_anno(r_anno):
    global annos, root, pg
    anno = tranform(pg, r_anno)
    tag_covered = anno.browse(root)
    # sgbox = get_suggest_box(anno)
    # if len(sgbox) > 0:
    #     # Gửi thôn báo có thể người dùng đánh dấu sai
    #     print (anno.x1, anno.y1, anno.x2, anno.y2)
    #     print (sgbox)
    # else :
    anno.elements = tag_covered
    annos.append(anno)

# @app.route('/finish', methods=['POST'])
def finish(url):
    global pg, root, annos, tree
    PATH_XML = 'pdf-file/' + url.split('/')[-1].split('.')[0] + '.xml'
    print (PATH_XML)
    for anno in annos:
        add_annotate_tag(anno)
    merge_annotate_tag(root)
    tree.write(PATH_XML, pretty_print=True)
    os.remove('pdf-file/tmp.xml')
    os.remove('pdf-file/tmp.pdf')
    pg, root, annos = (None, None, [])


def convert_xml(inf, outf, page_numbers=None, output_type='xml', codec='utf-8', laparams=None,
                maxpages=0, scale=1.0, rotation=0, output_dir=None, strip_control=False,
                debug=False, disable_caching=False):
    laparams = LAParams()
    imagewriter = None
    if output_dir:
        imagewriter = ImageWriter(output_dir)

    rsrcmgr = PDFResourceManager(caching=not disable_caching)

    device = XMLConverter(rsrcmgr, outf, codec='utf-8', laparams=laparams,
                          imagewriter=imagewriter,
                          stripcontrol=strip_control)

    interpreter = PDFPageInterpreter(rsrcmgr, device)
    for page in PDFPage.get_pages(inf,
                                  page_numbers,
                                  maxpages=maxpages,
                                  caching=not disable_caching,
                                  check_extractable=True):
        page.rotate = (page.rotate + rotation) % 360
        interpreter.process_page(page)
    device.close()
    return page


def tranform(page, r_anno):
    mediabox = page.mediabox
    x1 = r_anno['x'] - 2
    y1 = mediabox[3] - r_anno['y'] - r_anno['height'] - 2
    x2 = x1 + r_anno['width'] + 4
    y2 = y1 + r_anno['height'] + 4

    anno = Anno(x1, y1, x2, y2, r_anno['page'],
                r_anno['type'], r_anno['entity'])
    return anno


special_character = " !\"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"
def clear_xml(tag):
    if len(tag) > 0:
        for subtag in tag:
            clear_xml(subtag)
        if len(tag) == 0:
            tag.getparent().remove(tag)
    elif tag.tag == "text" and "bbox" not in tag.attrib:
        tag.getparent().remove(tag)
    elif tag.text is None:
        tag.getparent().remove(tag)
    elif not tag.text.isalpha() and not tag.text.isdigit() and tag.text not in special_character:
        tag.getparent().remove(tag)
    return tag


# Tìm khung của tag, là điểm trái nhất bên dưới và phải nhất bên trên
def get_border_of_elements(elements):
    bx1 = 99999
    by1 = 99999
    bx2 = -99999
    by2 = -99999
    for i in elements:
        x1, y1, x2, y2 = [float(x) for x in i.attrib['bbox'].split(',')]
        if x1 < bx1:
            bx1 = x1
        if y1 < by1:
            by1 = y1
        if x2 > bx2:
            bx2 = x2
        if y2 > by2:
            by2 = y2
    bbox = str(bx1) + ',' + str(by1) + ',' + str(bx2) + ',' + str(by2)
    return (bbox)


# def get_suggest_box(anno):
#     sgbox = []
#     if anno.bs[0] != 0 or anno.bs[1] != 0 or anno.bs[2] != 0 or anno.bs[3] != 0:
#         sgbox.append(anno.bs[0] + anno.x1)
#         sgbox.append(anno.bs[1] + anno.y1)
#         sgbox.append(anno.bs[2] + anno.x2)
#         sgbox.append(anno.bs[3] + anno.y2)
#     return sgbox


# Thêm khung anno
def add_annotate_tag(anno):
    for element in anno.elements:
        parent = element.getparent()
        index = parent.index(element)
        bbox = element.attrib['bbox']

        if parent.tag == "Annotate" and parent.attrib['label'] == anno.label and parent.attrib['bbox'] == bbox:
            continue

        anno_tag = etree.Element("Annotate")
        anno_tag.set("bbox", bbox)
        anno_tag.set("label", anno.label)
        anno_tag.insert(len(anno_tag), element)
        parent.insert(index, anno_tag)


# Gộp các tag anno liền nhau vào cùng 1 thẻ
def merge_annotate_tag(tag):
    index = 0
    while True:
        if index >= len(tag):
            break
        inner_tag = tag[index]
        merge_annotate_tag(inner_tag)
        if inner_tag.tag == "Annotate":
            anno_tag = etree.Element("Annotate")
            label = inner_tag.attrib['label']
            i = index
            while i < len(tag) and tag[i].tag == "Annotate" and tag[i].attrib['label'] == label:
                merge_annotate_tag(tag[i])
                for tg in tag[i]:
                    anno_tag.insert(len(anno_tag), tg)
                tag.remove(tag[i])
            anno_tag.set('bbox', get_border_of_elements(anno_tag))
            anno_tag.set('label', inner_tag.attrib['label'])
            tag.insert(index, anno_tag)
        index += 1


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=3000,
                        type=int, help='port listening')
    args = parser.parse_args()
    port = args.port
    app.debug = True
    app.run(host='0.0.0.0', port=port)
