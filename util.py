def is_number(s):
  s = s.replace(',','')
  try:
    float(s)
    return True
  except ValueError:
    pass

  try:
    import unicodedata
    unicodedata.numeric(s)
    return True
  except (TypeError,ValueError):
    pass
  return False