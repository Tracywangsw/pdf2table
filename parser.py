from bs4 import BeautifulSoup
import io
import os
import pdb
import numpy as np
import csv
from py4j.java_gateway import JavaGateway

hanlp = JavaGateway().entry_point
excel_forbidden_sign = ['+','-']

class Cell():
  def __init__(self,type,x,y,text):
    self.type = type
    self.x = x
    self.y = y
    self.text = text
    self.next = None
    self.pre = None

  def set_pre_cell(self,cell):
    self.pre = cell

  def set_next_cell(self,cell):
    self.next = cell

class Row(object):
  """docstring for Row"""
  def __init__(self,cell_list):
    self.cells = cell_list
    self.x_start = self.cells[0].x
    self.subrow_cells = self.set_subrow_cells()
    self.x_sequence = self.get_x_sequence()
    self.y_sequence = self.get_y_sequence()
    self.x_end = self.x_sequence[-1]
    self.set_cell_link()
    self.matrix = None

  def set_cell_link(self):
    for i in range(len(self.cells)-1):
      cell = self.cells[i]
      cell.next = self.cells[i+1]

  def set_subrow_cells(self):
    flag = set([self.cells[0].x])
    bound_cells = []
    for i in range(1,len(self.cells)):
      cur_cell = self.cells[i]
      pre_cell = self.cells[i-1]
      if cur_cell.x not in flag:
        flag.add(cur_cell.x)
      else:
        bound_cells.append(pre_cell)
        flag = set([cur_cell.x])
      if i == len(self.cells)-1: bound_cells.append(cur_cell)
    subrow_cells = {}
    subrow = 0
    for cell in self.cells:
      # pdb.set_trace()
      if subrow not in subrow_cells:
        subrow_cells[subrow] = [cell]
      else:
        subrow_cells[subrow].append(cell)
      if cell in bound_cells:
        subrow += 1
    return subrow_cells

  # get y_sequence from longest column
  def get_y_sequence(self):
    y_sequence = []
    long_columns = {}
    for cell in self.cells:
      if cell.x not in long_columns:
        long_columns[cell.x] = [cell.y]
      else:
        long_columns[cell.x].append(cell.y)
    max_column = 0
    for cell in self.cells:
      count_y = long_columns[cell.x]
      if len(count_y)>max_column:
        max_column = len(count_y)
        y_sequence = count_y
    if self.cells[0].y not in y_sequence:
      y_sequence.append(self.cells[0].y)
    return y_sequence

  def get_x_sequence(self):
    x_sequence = []
    for subrow,cells in self.subrow_cells.items():
      if cells[0].x not in x_sequence: x_sequence.append(cells[0].x)
      for i in range(1,len(cells)):
        cur_cell = cells[i]
        pre_cell = cells[i-1]
        if cur_cell.x not in x_sequence and pre_cell.x in x_sequence:
          index = x_sequence.index(pre_cell.x)+1
          x_sequence = x_sequence[:index] + [cur_cell.x]
    return x_sequence

  def set_matrix(self,subrow_num,subcol_num,offset):
    num = subrow_num*subcol_num
    matrix = np.array(['']*num,dtype=object).reshape(subrow_num,subcol_num)
    for cell in self.cells:
      if cell.y not in self.y_sequence or cell.x not in self.x_sequence: break
      cur_x = self.x_sequence.index(cell.x)
      next_x = len(self.x_sequence)
      if cell.next:
        if cell.next.x not in self.x_sequence: break
        next_x = self.x_sequence.index(cell.next.x)
        if next_x<=cur_x: next_x = len(self.x_sequence)
      cur_y = self.y_sequence.index(cell.y) # row
      for i in range(cur_y+1):
        for j in range(cur_x,next_x):
          if matrix[offset+i][j] == '':
            if cell.text[0] in excel_forbidden_sign: # filter for excel forbidden string
              matrix[offset+i][j] = ' '+cell.text
            else: matrix[offset+i][j] = cell.text
    self.matrix = matrix # if cell is not in sequence, return the matrix with ''
    return matrix



class Table(object):
  """docstring for Table"""
  def __init__(self, divs):
    self.divs = divs
    self.cells = self.__get_cell_info()
    self.rows = self.__get_rows()

  def __get_cell_info(self):
    cells = []
    for div in self.divs:
      div_class = div['class'] # list type
      cell = Cell(div_class[0],div_class[1],div_class[2],div.get_text())
      cells.append(cell)
    return cells

  def __get_rows(self):
    first_x = self.cells[0].x
    start = 0
    rows = []
    for i in range(1,len(self.cells)):
      cell = self.cells[i]
      if cell.x == first_x:
        row = Row(self.cells[start:i])
        rows.append(row)
        start = i
      if i == len(self.cells)-1:
        row = Row(self.cells[start:i+1])
        rows.append(row)
    # detect wheather row of y_sequence is right
    # find the convex cells of row
    convex_cells = {}
    for i in range(len(rows)):
      row = rows[i]
      for cell in row.cells:
        if cell.y not in row.y_sequence:
          convex_cells[cell] = [i]
        else:
          cur_index = row.y_sequence.index(cell.y)
          if cur_index>len(row.y_sequence)-1: # this row is not a rectangle
            convex_cells[cell] = [i]
    if convex_cells: # convex_cells exist
      # add row index for convex cells
      for cell,row_indexs in convex_cells.items():
        init_row = row_indexs[0]
        for j in range(init_row+1,len(rows)):
          row = rows[j]
          convex_cells[cell].append(j)
          if row.cells[0].y == cell.y: # first cell of row(for now maybe need changing)
            break
      # row merge range
      min_r = len(rows); max_r = 0
      for cell,ranges in convex_cells.items():
        if ranges[0]<min_r: min_r = ranges[0]
        if ranges[-1]>max_r: max_r = ranges[-1]
      # rebuild row
      merge_cells = []
      for i in range(min_r,max_r+1):
        r = rows[i]
        merge_cells += r.cells
      new_big_row = Row(merge_cells)
      if max_r<len(rows)-1:
        rows = rows[:min_r]+[new_big_row]+rows[max_r+1:]
      else:
        rows = rows[:min_r]+[new_big_row]
    return rows

  def table2matrix(self):
    x_sequence = self.rows[0].x_sequence
    max_x_sequence = x_sequence
    for row in self.rows:
      if len(row.x_sequence)>len(max_x_sequence):
        max_x_sequence = row.x_sequence

    matrix_row_num = 0
    for row in self.rows:
      matrix_row_num += len(row.y_sequence)
      row.x_sequence = max_x_sequence

    r = matrix_row_num; c = len(max_x_sequence)
    t_matrix = np.array(['']*(r*c),dtype=object).reshape(r,c)
    i = 0
    for row in self.rows:
      row.set_matrix(r,c,i)
      t_matrix += row.matrix
      i += len(row.y_sequence)
    return t_matrix


class Pdf2Table(object):
  """docstring for Table"""
  def __init__(self,pdf_path):
    self.html,self.pages = self.load_html(pdf_path)
    self.tables = self.__get_embedding_tables()
    self.text = self.__get_embedding_text()

  def __get_embedding_tables(self):
    page_tables = {} # rude_table per page
    for p in range(len(self.pages)):
      rude_tables = self.extract_table_divs(self.pages[p])
      if rude_tables:
        page_tables[p] =[]
        for t in rude_tables:
          page_tables[p].extend(self.all_tables(t))

    result = {} # all tables per page
    for page,tables in page_tables.items():
      print(page)
      for t in tables:
        # if page == 57: pdb.set_trace()
        t_matrix = Table(t).table2matrix()
        # pdb.set_trace()
        info = self.get_table_info(t,page)
        if page not in result:
          result[page] = [(t_matrix.tolist(),info)]
        else:
          result[page].append((t_matrix.tolist(),info))
    return result

  def __get_embedding_text(self):
    page_text = {}
    segment = [' ']
    document = ''
    for p in range(len(self.pages)):
      page_text[p] = self.extract_text(self.pages[p])
      if page_text[p]: document += page_text[p]
    paragraphs = []
    if document:
      paragraphs = document.split(' ')
    return paragraphs

  def get_div_bottom(self,css_class,endstr):
    bottom = ''
    if css_class:
      query = '.'+css_class+'{bottom:'
      start = self.html.find(query)
      if start != -1:
        start += len(query)
        end = self.html.find(endstr,start)
        bottom = self.html[start:end]
        bottom = bottom[:len(bottom)-2]
    return bottom

  def extract_text(self,page):
    content_divs = page.select(".pc > div")
    if not content_divs: return
    div_bottom = {}
    for i in range(len(content_divs)):
      div = content_divs[i]
      div_class = div['class'] # list type
      div_type = div_class[0]
      div_y = ''
      for c in div_class:
        if 'y' in c: div_y = c
      if div_y:
        bottom = self.get_div_bottom(div_y,';}')
        div_bottom[i] = float(bottom)
    start_div = len(content_divs)
    for i in range(len(content_divs)-1):
      if i in div_bottom and i+1 in div_bottom:
        cur_div = div_bottom[i]
        next_div = div_bottom[i+1]
        if next_div-cur_div>500: # if div distance big than 500px,so that the current div is the page
          start_div = i+1
          break
    text = ''
    for j in range(start_div,len(content_divs)):
      if content_divs[j]['class'][0] == 't':
        content = content_divs[j].get_text()
        if content and content.strip() != '':
          content = content[:len(content)-1].replace(' ','')+content[-1]
          text += content
    return text

  # return html pages
  def load_html(self,filename):
    lines = []
    with io.open(filename,'r',encoding='utf-8') as f:
      for line in f:
        lines.append(line.strip())
    html = ''.join(lines)
    soup = BeautifulSoup(html,'html.parser')
    pages = soup.select("#page-container > div")
    return html,pages

  def extract_table_divs(self,page):
    content_divs = page.select(".pc > div")
    if not content_divs: return
    div_type_list = []
    for div in content_divs:
      div_class = div['class'] # list type
      div_type = div_class[0]
      div_type_list.append(div_type)
    table_ranges = self.find_continue_list(div_type_list)
    if not table_ranges: return
    tables = []; description = ''
    for r in table_ranges:
      tables.append(content_divs[r[0]:r[1]])
    return tables

  # find table range,return the range [start:end] list of tables
  def find_continue_list(self,type_list):
    table_range_list = []
    if not type_list: return
    start = 0
    while start<len(type_list)-1:
      # pdb.set_trace()
      if type_list[start] == "c":
        end = start+1
        for j in range(start+1,len(type_list)):
          if type_list[j] == "t":
            end = j
            if end - start > 1: table_range_list.append([start,end])
            break
        if j == len(type_list)-1:
          if type_list[j] == "c": table_range_list.append([start,j+1])
          break
        start = end
      start += 1
    return table_range_list

  # remove the div neither x nor y is the same as the others'
  def remove_single_div(self,table_divs):
    x_start = table_divs[0]['class'][1]
    count_y = {}
    count_x = {}
    for div in table_divs:
      x = div['class'][1]
      y = div['class'][2]
      if x not in count_x:
        count_x[x] = 1
      else:
        count_x[x] += 1
      if y not in count_y:
        count_y[y] = 1
      else:
        count_y[y] += 1

    break_point = []
    i = 0
    for div in table_divs:
      x = div['class'][1]
      y = div['class'][2]
      if count_x[x] == 1 and count_y[y] == 1:
        break_point.append(i)
      i += 1

    for j in range(len(break_point)):
      p = break_point[j]
      if j == len(break_point)-1: table_divs = table_divs[:p]
      else: table_divs = table_divs[:p]+ table_divs[p+1:]
    return table_divs

  # find the bound of the table
  def clean_table_divs(self,table_divs):
    table_divs = self.remove_single_div(table_divs)
    table,spare = [],[]
    if table_divs:
      first_x = table_divs[0]['class'][1]
      first_x_point = []
      for i in range(len(table_divs)):
        div = table_divs[i]
        x = div['class'][1]
        y = div['class'][2]
        if x == first_x:
          first_x_point.append(i)
      print('first_x_point: '+str(first_x_point))

      # find the last cell of the table
      if len(first_x_point)>1:
        last_row_div = table_divs[first_x_point[-1]]
        last_y = last_row_div['class'][2]
        last_div_y = table_divs[-1]['class'][2]
        end_point = first_x_point[-1]
        if last_div_y == last_y: return table_divs,[]
        for d in range(first_x_point[-1],len(table_divs)):
          cur_y = table_divs[d]['class'][2]
          pre_div_y = table_divs[d-1]['class'][2]
          if cur_y != last_y and pre_div_y == last_y:
            end_point = d
        table = table_divs[:end_point]
        spare = table_divs[end_point:]
      else:
        print('first_x_point is too small: '+str(first_x_point))
    return table,spare

  def get_table_info(self,table,page):
    table_info = []
    first_cell_class = ' '.join(table[0]['class'])
    first_cell_soup = self.pages[page].find('div',{"class":first_cell_class})
    if first_cell_soup:
      info_divs = first_cell_soup.previous_siblings
      count_info = 0
      for info_div in info_divs:
        if count_info == 2: break
        table_info.append(info_div.text)
        count_info += 1
    table_info.reverse()
    info = ' '.join(table_info)
    return info

  def all_tables(self,table_divs):
    table_divs = self.remove_single_div(table_divs)
    tables = []
    while len(table_divs)>1:
      table,table_divs = self.clean_table_divs(table_divs)
      if table: tables.append(table)
    return tables

  def write_table_csv(self,output_path):
    sort_page = [p for p in self.tables.keys()]
    sort_page.sort()
    for page in sort_page:
      table_list = self.tables[page]
      for table in table_list:
        t = table[0]
        info = table[1]
        r_list = [['']*len(t[0])]
        r_list.append(['page:'+str(page),info]+['']*(len(t[0])-2))
        r_list.extend(t)
        with open(output_path,'a') as f:
          a = csv.writer(f,delimiter=',')
          a.writerows(r_list)

  def write_text_txt(self,txt_path):
    # sort_page = [p for p in self.text.keys()]
    # sort_page.sort()
    # t_list = []
    # for page in sort_page:
    #   text = self.text[page]
    #   t_list.append([''])
    #   t_list.append(['page:'+str(page)])
    #   t_list.append([text])
    #   if text:
    #     summary = hanlp.TextSummarization(text,3)
    #     key_words = hanlp.Keyword(text,10)
    #     t_list.append(summary)
    #     t_list.append(key_words)
    if self.text:
      t_list = []
      for t in self.text:
        t_list.append([' '])
        t_list.append([t])
        summary = hanlp.TextSummarization(t,4)
        key_words = hanlp.Keyword(t,4)
        t_list.append(summary)
        t_list.append(key_words)
      with open(txt_path,'w') as f:
        t = csv.writer(f,delimiter=',')
        t.writerows(t_list)



def pdf2html_bash(dest_dir,filename):
  command = "pdf2htmlEX --zoom 1.3 --dest-dir '"+dest_dir+"' '"+filename+"'"
  print(command)
  os.system(command)

def go(input_pdf_dir='./sample/test/pdf/',html_dir='./sample/test/html/',output_table_dir='./sample/test/table/',output_text_dir='./sample/test/text/'):
  # pdf to html
  # for dirname,dirnames,filenames in os.walk(input_pdf_dir):
  #   for filename in filenames:
  #     if filename.endswith('.pdf'):
  #       newname = filename.replace(' ','')
  #       os.rename(os.path.join(dirname,filename),os.path.join(dirname,newname))
  #       input_pdf = os.path.join(dirname,newname)
  #       print('input pdf: '+input_pdf)
  #       pdf2html_bash(html_dir,input_pdf)

  # html to csv
  for dirname,dirnames,filenames in os.walk(html_dir):
    for filename in filenames:
      if filename.endswith('.html'):
        input_html = os.path.join(dirname,filename)
        print(input_html)
        h = Pdf2Table(input_html)
        output_filename = filename[:-5]+'.csv'
        table_path = output_table_dir+output_filename
        text_path = output_text_dir+output_filename
        h.write_table_csv(table_path)
        h.write_text_txt(text_path)

if __name__ == "__main__":
  print('begin')
  go()

def load_html(filename):
  lines = []
  with io.open(filename,'r',encoding='utf-8') as f:
    for line in f:
      lines.append(line.strip())
  html = ''.join(lines)
  # soup = BeautifulSoup(html,'html.parser')
  # import cssutils
  # sheets = []
  # for styletag in soup.findAll('style',type='text/css'):
  #   if not styletag.string:
  #    continue
  #   sheets.append(cssutils.parseStyle(styletag.string))
  return html

