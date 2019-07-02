class Anno:
    def __init__(self, x1, y1, x2, y2, page, annotype, label):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.page = page
        self.label = label
        self.annotype = annotype
        self.elements = []
        self.bs = [0, 0, 0, 0]
        self.suggest = [x1-10, y1-10,x2+10,y2+10]
        
    # Kiểm tra xem đối tượng Anno đang xét có bao hoàn toàn tag không
    def is_covered(self, tag):
        if "bbox" not in tag.attrib:
            return False
        tagx1, tagy1, tagx2, tagy2 = [float(x) for x in tag.attrib['bbox'].split(',')]
        if self.x1 <= tagx1 and self.y1 <= tagy1 and self.x2 >= tagx2 and self.y2 >= tagy2:
            return True
        else: 
            return False
        
        
    # Kiểm tra xem đối tượng Anno đang xét có hoàn toàn không chồng lên tag không
    def is_completely_not_covered(self, tag):
        if "bbox" not in tag.attrib:
            return True
        tagx1, tagy1, tagx2, tagy2 = [float(x) for x in tag.attrib['bbox'].split(',')]
        if self.x1 > tagx2 or self.x2 < tagx1 or self.y1 > tagy2 or self.y2 < tagy1:
            return True
        else :
            return False


    def is_nearly_covered(self, tag):
        tagx1, tagy1, tagx2, tagy2 = [float(x) for x in tag.attrib['bbox'].split(',')]  
        k1 = [self.x1, self.x2, tagx1, tagx2]
        k1.sort()
        subx1, subx2 = k1[1:3]
        k2 = [self.y1, self.y2, tagy1, tagy2]
        k2.sort()
        suby1, suby2 = k2[1:3]
        if tag.tag == "textbox" and tag.attrib['id'] == '3' and self.label == "PeIn":
            print (tag.attrib['bbox'])
            print (self.x1, self.y1, self.x2, self.y2)
            print ("leu leu")
            print (subx1, suby1, subx2, suby2)
            print ("leu leu")

        if (subx2 - subx1) / (tagx2 - tagx1) >= 0.8 and (suby2 - suby1) / (tagy2 - tagy1) >= 0.8:
            return True
        else :
            return False
        
    # Tạo gợi ý cho anno nếu người dùng nhập thiếu
    def cal_suggestion (self, tag):
        if "bbox" not in tag.attrib:
            return
        tagx1, tagy1, tagx2, tagy2 = [float(x) for x in tag.attrib['bbox'].split(',')]
        if self.suggest[0] <= tagx1 and self.suggest[1] <= tagy1 and self.suggest[2] >= tagx2 and self.suggest[3] >= tagy2:
            if tagx1 <= self.x1 and self.x1 <= tagx1 + 10 :
                self.bs[0] = tagx1 - self.x1 
            if tagy1 <= self.y1 and self.y1 <= tagy1 + 10 :
                self.bs[1] = tagy1 - self.y1
            if tagx2 >= self.x2 and self.x2 >= tagx2 - 10 :
                self.bs[2] = tagx2 - self.x2
            if tagy2 >= self.y2 and self.y2 >= tagy2 - 10 :
                self.bs[3] = tagy2 - self.y2
    
        
    # Lấy danh sách tất cả những tag con của biến tag nằm trong hoặc gần trong đối tượng Anno
    def browse(self, tag):
        tag_covered = []
        for inner_tag in tag:
            if inner_tag.tag == "page" and int(inner_tag.attrib["id"]) != self.page:
                continue
            if self.is_covered (inner_tag):
                tag_covered.append(inner_tag)
            elif not self.is_completely_not_covered(inner_tag):
                if self.is_nearly_covered(inner_tag):
                    tag_covered.append(inner_tag)
                else :
                    tc = self.browse(inner_tag)
                    if len(tc) > 0: tag_covered += tc
        return tag_covered