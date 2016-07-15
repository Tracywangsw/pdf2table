import pdb
import numpy as np

excel_forbidden_sign = ['+','-']

class Cell():
  def __init__(self,type,x,y,text):
    self.type = type
    self.x = x
    self.y = y
    self.text = text
    self.row = 1
    self.column = 1
    self.covers = []
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
      cur_y = self.y_sequence.index(cell.y)
      for i in range(cur_y+1): #row
        for j in range(cur_x,next_x): # column
          if matrix[offset+i][j] == '':
            if cur_y == i and cur_x == next_x-1:
              if cell.text[0] in excel_forbidden_sign: # filter for excel forbidden string
                matrix[offset+i][j] = ' '+cell.text
              else: matrix[offset+i][j] = cell.text
            else:
              if cell.text[0] in excel_forbidden_sign: # filter for excel forbidden string
                matrix[offset+i][j] = ' '+cell.text+"#merge#"
              else: matrix[offset+i][j] = cell.text+"#merge#"
    self.matrix = matrix # if cell is not in sequence, return the matrix with ''
    return matrix

  # for merging cells
  def set_cell_covers(self,offset):
    position_set = set()
    for cell in self.cells:
      if cell.y not in self.y_sequence or cell.x not in self.x_sequence: break
      cur_x = self.x_sequence.index(cell.x)
      next_x = len(self.x_sequence)
      if cell.next:
        if cell.next.x not in self.x_sequence: break
        next_x = self.x_sequence.index(cell.next.x)
        if next_x<=cur_x: next_x = len(self.x_sequence)
      cur_y = self.y_sequence.index(cell.y)
      cell.row = cur_y+1
      cell.column = next_x-cur_x
      for i in range(cur_y+1): #row
        for j in range(cur_x,next_x): #column
          position = (offset+i,j)
          if position not in position_set:
            cell.covers.append(position)
            position_set.add(position)


class Table(object):
  """docstring for Table"""
  def __init__(self, divs):
    self.divs = divs
    self.cells = self.__get_cell_info()
    self.rows = self.__get_rows()
    self.size = self.__get_table_size() # tuple (row,column)
    self.info = None

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

  def __get_table_size(self):
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
    return (r,c)

  def table2matrix(self):
    r = self.size[0]; c = self.size[1]
    t_matrix = np.array(['']*(r*c),dtype=object).reshape(r,c)
    i = 0
    for row in self.rows:
      row.set_matrix(r,c,i)
      t_matrix += row.matrix
      i += len(row.y_sequence)
    return t_matrix

  # for merging cells
  def set_table_cells(self,offset):
    i = 0
    for row in self.rows:
      row.set_cell_covers(offset+i)
      i += len(row.y_sequence)