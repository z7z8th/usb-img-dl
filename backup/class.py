

class abc(object):
    pass

aa = object()
aa.a = 1
aa.b = 2
aa.c = [3,4]

print aa.__dict__

print "-" * 30

print aa.__builtins__

