from bs4 import BeautifulSoup
import io
import os
import pdb
import numpy as np
import csv
from py4j.java_gateway import JavaGateway
import table_structure
from openpyxl.workbook import Workbook
import xlwt
import util

hanlp = JavaGateway().entry_point

class Pdf2Table(object):
  """docstring for Table"""
  def __init__(self,pdf_path):
    self.html,self.pages = self.load_html(pdf_path)
    self.page_tables = self.__get_page_tables()
    self.text = self.__get_embedding_text()
    # self.tables = self.__get_embedding_tables()

  def __get_page_tables(self):
    page_tables = {} # rude_table per page
    for p in range(len(self.pages)):
      # pdb.set_trace()
      rude_tables = self.extract_table_divs(self.pages[p])
      if rude_tables:
        page_tables[p] =[]
        for t in rude_tables:
          page_tables[p].extend(self.all_tables(t))
    return page_tables

  def write_table(self,path):
    if not self.page_tables: return
    # page sort
    sort_page = [p for p in self.page_tables.keys()]
    sort_page.sort()
    # set cell covers
    i = 1
    for page in sort_page:
      tables = self.page_tables[page]
      self.page_tables[page] = []
      for t in tables:
        info = self.get_table_info(t,page)
        tt = table_structure.Table(t)
        tt.info = info
        tt.set_table_cells(i)
        # pdb.set_trace()
        i += tt.size[0]+2
        self.page_tables[page].append(tt)
    # write tables in excel
    wb = xlwt.Workbook()
    sheet = wb.add_sheet('tables',cell_overwrite_ok=True)
    j = 0
    for page in sort_page:
      tables = self.page_tables[page]
      for table in tables:
        sheet.write(j,0,"page "+str(page+1))
        sheet.write(j,1,table.info)
        j += table.size[0]+2
        for cell in table.cells:
          if cell.covers:
            if len(cell.covers)>1:
              top_row = cell.covers[0][0]
              bottom_row = cell.covers[-1][0]
              left_column = cell.covers[0][1]
              right_column = cell.covers[-1][1]
              if util.is_number(cell.text): # if cell.text is number, save in number style
                content = cell.text.replace(',','')
                sheet.write_merge(top_row, bottom_row, left_column, right_column, float(content))
              else:
                sheet.write_merge(top_row, bottom_row, left_column, right_column, cell.text)
            else:
              if util.is_number(cell.text):
                content = cell.text.replace(',','')
                sheet.write(cell.covers[0][0],cell.covers[0][1],float(content))
              else:
                sheet.write(cell.covers[0][0],cell.covers[0][1],cell.text)
    wb.save(path)

  def __get_embedding_tables(self):
    if not self.page_tables: return
    result = {} # all tables per page
    for page,tables in self.page_tables.items():
      print(page)
      for t in tables:
        t_matrix = table_structure.Table(t).table2matrix()
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
    with io.open(filename,'r',errors='ignore') as f:
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
    # pdb.set_trace()
    origin_len = len(table_divs)
    # for j in range(len(break_point)):
    #   p = break_point[j]
    #   if len(break_point) != 1 and p == origin_len-1: first_clean_divs = table_divs[:p]
    #   else: first_clean_divs = table_divs[:p]+ table_divs[p+1:]
    first_clean_divs = []
    for d in range(len(table_divs)):
      if d not in break_point:
        first_clean_divs.append(table_divs[d])
    return first_clean_divs

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
      # print('first_x_point: '+str(first_x_point))

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
      # else:
      #   print('first_x_point is too small: '+str(first_x_point))
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
    if self.text:
      t_list = []
      document = ''
      for t in self.text:
        document += t+'\n'
      if document:
        print('------Generating text summary and Extracting text keywords------')
        summary = hanlp.TextSummarization(document,10)
        key_words = hanlp.Keyword(document,10)
        t_list.append([document])
        t_list.append(summary)
        t_list.append(key_words)
      with open(txt_path,'w') as f:
        k = csv.writer(f,delimiter=',')
        k.writerows(t_list)



def pdf2html_bash(dest_dir,filename):
  command = "pdf2htmlEX --zoom 1.3 --dest-dir '"+dest_dir+"' '"+filename+"'"
  os.system(command)

def go(input_pdf_dir='./debug/',page_count_path='./page_count.csv'):
  # pdf to html
  for dirname,dirnames,filenames in os.walk(input_pdf_dir):
    for filename in filenames:
      if filename.endswith('.pdf'):
        newname = filename.replace(' ','')
        os.rename(os.path.join(dirname,filename),os.path.join(dirname,newname))
        input_pdf = os.path.join(dirname,newname)
        print('input pdf: '+input_pdf)
        print(dirname)
        start = len(input_pdf_dir)
        newdir = dirname[start:]
        input_dir = input_pdf_dir+"html/"+newdir
        if not os.path.exists(input_dir):
          os.makedirs(input_dir)
        pdf2html_bash(input_dir,input_pdf)

  # html to csv
  html_dir = input_pdf_dir+"html/"
  page_count = []
  for dirname,dirnames,filenames in os.walk(html_dir):
    for filename in filenames:
      if filename.endswith('.html'):
        input_html = os.path.join(dirname,filename)
        print(input_html)
        h = Pdf2Table(input_html)
        output_filename = filename[:-5]
        page_count.append((output_filename,len(h.pages)))
        output_dir = input_pdf_dir+"ouput/"+dirname[len(input_pdf_dir):]
        if not os.path.exists(output_dir):
          os.makedirs(output_dir)
        table_path = output_dir+"/table-"+output_filename+'.xls'
        text_path = output_dir+"/text-"+output_filename+'.csv'
        print('write csv file')
        # h.write_table_csv(table_path)
        h.write_table(table_path)
        h.write_text_txt(text_path)
  with open(page_count_path,'w') as f:
    k = csv.writer(f,delimiter=',')
    k.writerows(page_count)


if __name__ == "__main__":
  print('begin')
  go()
  print('end')

def load_html(filename):
  lines = []
  with open(filename,'r',errors='ignore') as f:
    for line in f:
      lines.append(line.strip())
  html = ''.join(lines)
  soup = BeautifulSoup(html,'html.parser')
  pages = soup.select("#page-container > div")
  return html,pages