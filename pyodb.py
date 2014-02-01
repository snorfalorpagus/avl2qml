#!/usr/bin/env python

'''
pyodb - module for reading ArcView 3.x Object Database files
'''

import re

class ODB(object):
    def __init__(self, odbstr):
        # parse input data
        self.objects = {}
        buf = []
        for line in odbstr.split('\n'):
            line = line.rstrip()
            if len(line) == 0 or line[0] == '/':
                continue
            if line[0] == '\t' or (line[0] == '(' and len(buf) == 0):
                buf.append(line)
            elif line == ')':
                match = re.search('\((.*)\.([0-9]*)', buf[0])
                if match is not None:
                    odb_object_type, pkid = match.groups()
                    pkid = int(pkid)
                    try:
                        obj = special_objects[odb_object_type](self, odb_object_type, pkid, buf[1:])
                    except KeyError:
                        obj = ODBObject(self, odb_object_type, pkid, buf[1:])
                    self.objects[pkid] = obj
                buf = []
            else:
                buf[-1] += line + '\n'
        # resolve object references
        legend = None
        for pkid, obj in sorted(self.objects.items()):
            obj.resolve_references()
            if isinstance(obj, ODBObject_Legend):
                legend = obj
        # link symbols to legend classes, for convenience
        if legend is not None:
            symlist = legend.symbols
            symbol_idx = 0
            if hasattr(legend.classes, '__iter__') is False:
                legend.classes = [legend.classes]
                symlist.symbols = [symlist.symbols]
            for legend_idx in range(0, len(legend.classes)):
                if 'IsNoData' not in legend.classes[legend_idx].attrs:
                    legend.classes[legend_idx].symbol = symlist.symbols[symbol_idx]
                    symbol_idx += 1

class ODBObject(object):
    '''Generic ODB object'''
    def __init__(self, odb, odb_object_type, pkid, attrs):
        self.odb = odb
        self.object_type = odb_object_type
        self.pkid = pkid
        # parse attributes
        self.attrs = {}
        for attr in attrs:
            match = re.match('\t?([^\:]{1,})\:\t(.*)', attr, re.DOTALL)
            if match:
                key, value = match.groups()
                match_int = re.match('^([0-9\-\+]{1,})$', value)
                if match_int: # value is an integer
                    self.append_attr(key, int(value))
                    continue
                match_float = re.match('^([0-9\.\-\+]{1,})$', value)
                if match_float: # value is a float
                    self.append_attr(key, float(value))
                    continue
                # value is a string
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                self.append_attr(key, value)

    def append_attr(self, key, value):
        if key not in self.attrs:
            self.attrs[key] = value
        elif isinstance(self.attrs[key], list):
            self.attrs[key].append(value)
        else:
            self.attrs[key] = [self.attrs[key], value,]

    def resolve_references(self):
        pass # overridden by subclasses

    def resolve(self, name, key):
        '''Resolve a reference using it's pkid'''
        if isinstance(self.attrs[key], list):
            setattr(self, name, [self.odb.objects[k] for k in self.attrs[key]])
        else:
            setattr(self, name, self.odb.objects[self.attrs[key]]) 

    def get_data(self, key='Data'):
        '''Decode hexidecimal data stored in a 'Data' attribute'''
        if isinstance(self.attrs[key], list):
            data = ''.join(self.attrs[key])
        else:
            data = self.attrs[key]
        data = data.replace(' ', '')
        return data.decode('hex')
    data = property(get_data)

class ODBObject_TClr(ODBObject):
    '''
    Color
    '''
    def __init__(self, *args, **kwargs):
        ODBObject.__init__(self, *args, **kwargs)
        colors = ('Red', 'Green', 'Blue',)
        for color in colors:
            if color in self.attrs:
                setattr(self, color.lower(), int(self.attrs[color], 0))
            else:
                setattr(self, color.lower(), 0)
        if 'Name' in self.attrs and self.attrs['Name'] == 'Transparent':
            self.alpha = 0
        else:
            self.alpha = 65535
        self.rgba_16bit = (self.red, self.green, self.blue, self.alpha)
        self.rgba_8bit = tuple([color/256 for color in self.rgba_16bit])

class ODBObject_Legend(ODBObject):
    '''Legend'''
    def resolve_references(self):
        self.resolve('symbols', 'Symbols')
        self.resolve('classes', 'Class')
        try:
            self.resolve('field_names', 'FieldNames')
        except KeyError:
            pass

class ODBObject_LClass(ODBObject):
    '''Legend class'''
    def __init__(self, *args, **kwargs):
        ODBObject.__init__(self, *args, **kwargs)
        self.label = self.attrs['Label']

class ODBObject_SymList(ODBObject):
    '''Symbol list'''
    def resolve_references(self):
        self.resolve('symbols', 'Child')

class ODBObject_BShSym(ODBObject):
    '''Polygon symbol'''
    def resolve_references(self):
        self.resolve('color', 'Color')
        self.resolve('bgcolor', 'BgColor')
        self.resolve('outlinecolor', 'OutlineColor')
        self.outlinewidth = self.attrs['OutlineWidth']
        if 'Stipple' in self.attrs:
            self.resolve('stipple', 'Stipple')

class ODBObject_BLnSym(ODBObject):
    '''BLine symbol''' # B = basic?
    def resolve_references(self):
        self.resolve('color', 'Color')
        self.width = self.attrs['Width']

class ODBObject_CLnSym(ODBObject):
    '''CLine symbol''' # C = complex?
    def resolve_references(self):
        self.resolve('color', 'Color')
        self.resolve('symbols', 'Symbols')

special_objects = {
    'Legend': ODBObject_Legend,
    'LClass': ODBObject_LClass,
    'TClr': ODBObject_TClr,
    'SymList': ODBObject_SymList,
    'BShSym': ODBObject_BShSym,
    'BLnSym': ODBObject_BLnSym,
    'CLnSym': ODBObject_CLnSym,
}
