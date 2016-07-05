
class Node(object):
  """docstring for Node"""
  def __init__(self,data):
    self.data = data
    self.next = None
    self.pre = None

class LinkedList(object):
  """docstring for LinkedList"""
  def __init__(self):
    self.cur_node = None
    self.val_set = None

  def add_node(self,data):
    new_node = Node(data)
    new_node.next = self.cur_node
    self.cur_node = new_node
    self.val_set.add(data)

  def to_array(self):
    array = []
    node = self.cur_node
    while node:
      array.append(node.data)
      node = node.next
    array.reverse()
    return array

  @classmethod
  def array2linked(cls,array):
    if array == None: return


