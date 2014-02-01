#!/usr/bin/env python

'''
avl2qml - module for converting ArcView 3.x Legends (.avl) to QGIS styles (.qml)
'''

import argparse
import xml.etree.ElementTree as ET
import os
import re

import pyodb

def avl2qml(data, shapefile=None, field_name=None):
    # parse avl
    odb = pyodb.ODB(data)
    legend = odb.objects[1].attrs['Roots'] # assumes legend is the first root
    if isinstance(legend, list):
        legend = odb.objects[legend[0]]
    else:
        legend = odb.objects[legend]

    # create qml style document
    qgis = ET.fromstring('<qgis version="2.0.1-Dufour" minimumScale="-4.65661e-10" maximumScale="1e+08" minLabelScale="0" maxLabelScale="1e+08" hasScaleBasedVisibilityFlag="0" scaleBasedLabelVisibilityFlag="0" />')
    renderer = ET.SubElement(qgis, 'renderer-v2', {'symbollevels': '0'})

    if field_name is None:
        # include field name, if it's specified
        if hasattr(legend, 'field_names'):
            field_name = legend.field_names.attrs['S']
            if shapefile is not None:
                # attempt to correct case of field name
                import ogr
                ds = ogr.Open(shapefile)
                layer = ds.GetLayer()
                defn = layer.GetLayerDefn()
                for n in range(0, defn.GetFieldCount()):
                    name = defn.GetFieldDefn(n).GetName()
                    if field_name.lower() == name.lower():
                        field_name = name
            renderer.attrib['attr'] = field_name
    else:
        renderer.attrib['attr'] = field_name

    if legend.attrs['LegType'] == '0x01':
        # single symbol
        renderer.attrib['type'] = 'singleSymbol'
    if legend.attrs['LegType'] == '0x02':
        # graduated symbols
        ranges = ET.SubElement(renderer, 'ranges')
        renderer.attrib['type'] = 'graduatedSymbol'
    elif legend.attrs['LegType'] == '0x08':
        # categorized symbols
        categories = ET.SubElement(renderer, 'categories')
        renderer.attrib['type'] = 'categorizedSymbol'

    symbols = ET.SubElement(renderer, 'symbols')

    n = 0
    for lclass in legend.classes:
        if hasattr(lclass, 'symbol'):

            # define class

            if legend.attrs['LegType'] == '0x01':

                pass # nothing to do here

            elif legend.attrs['LegType'] == '0x02':

                rng = ET.SubElement(ranges, 'range')
                rng.attrib['symbol'] = str(n)
                # HACK: QGIS doesn't match '1.0' to '1'
                if lclass.attrs['MinNum'] == int(lclass.attrs['MinNum']):
                    rng.attrib['lower'] = str(int(lclass.attrs['MinNum']))
                else:
                    rng.attrib['lower'] = str(lclass.attrs['MinNum'])
                if lclass.attrs['MaxNum'] == int(lclass.attrs['MaxNum']):
                    rng.attrib['upper'] = str(int(lclass.attrs['MaxNum']))
                else:
                    rng.attrib['upper'] = str(lclass.attrs['MaxNum'])
                if lclass.label is not None:
                    rng.attrib['label'] = lclass.label
                else:
                    rng.attrib['label'] = ''

            elif legend.attrs['LegType'] == '0x08':

                category = ET.SubElement(categories, 'category')
                category.attrib['symbol'] = str(n)
                if 'MinNum' in lclass.attrs:
                    if lclass.attrs['MinNum'] == int(lclass.attrs['MinNum']):
                        # HACK: QGIS doesn't match '1.0' to '1'
                        category.attrib['value'] = str(int(lclass.attrs['MinNum']))
                    else:
                        category.attrib['value'] = str(lclass.attrs['MinNum'])
                else:
                    category.attrib['value'] = lclass.attrs['MinStr']
                if lclass.label is not None:
                    category.attrib['label'] = lclass.label
                else:
                    category.attrib['label'] = ''

            # define symbol for class

            symbol = ET.SubElement(symbols, 'symbol')
            symbol.attrib['name'] = str(n)
            symbol.attrib['alpha'] = '1'

            if legend.attrs['SymType'] == '0x01':

                # symbol type is line
                symbol.attrib['type'] = 'line'

                if hasattr(lclass.symbol, 'color') or 1:
                    layer1 = ET.SubElement(symbol, 'layer')
                    layer1.attrib['pass'] = '0'
                    layer1.attrib['class'] = 'SimpleLine'
                    layer1.attrib['locked'] = '0'
                    properties = {
                        'capstyle': 'square',
                        'color': ','.join([str(x) for x in lclass.symbol.color.rgba_8bit]),
                        'customdash': '5;2',
                        'customdash_unit': 'MM',
                        'joinstyle': 'bevel',
                        'offset': '0',
                        'offset_unit': 'MM',
                        'penstyle': 'solid',
                        'use_custom_dash': '0',
                        'width_unit': 'MM',
                    }
                    if hasattr(lclass.symbol, 'width'):
                        properties['width'] = str(lclass.symbol.width * 0.26)
                    else:
                        properties['width'] = '0.26'
                    for k,v in list(properties.items()):
                        prop = ET.SubElement(layer1, 'prop')
                        prop.attrib['k'] = k
                        prop.attrib['v'] = v

            elif legend.attrs['SymType'] == '0x02':

                # symbol type is fill
                symbol.attrib['type'] = 'fill'

                layer1 = ET.SubElement(symbol, 'layer')
                layer1.attrib['pass'] = '0'
                layer1.attrib['class'] = 'SimpleFill'
                layer1.attrib['locked'] = '0'
                properties = {
                    'border_width_unit': 'MM',
                    'color_border': ','.join([str(x) for x in lclass.symbol.outlinecolor.rgba_8bit]),
                    'offset': '0,0',
                    'offset_unit': 'MM',
                    'style': 'solid',
                    'style_border': 'solid',
                    'width_border': str(lclass.symbol.outlinewidth*0.26),
                }
                if 'Stipple' not in lclass.symbol.attrs:
                    properties['color'] = ','.join([str(x) for x in lclass.symbol.color.rgba_8bit])
                else:
                    properties['color'] = ','.join([str(x) for x in lclass.symbol.bgcolor.rgba_8bit])
                for k,v in list(properties.items()):
                    prop = ET.SubElement(layer1, 'prop')
                    prop.attrib['k'] = k
                    prop.attrib['v'] = v

                if 'Stipple' in lclass.symbol.attrs:
                    # don't know how to render 'Stipple' correctly - just use hatching instead
                    layer2 = ET.SubElement(symbol, 'layer')
                    layer2.attrib['pass'] = '0'
                    layer2.attrib['class'] = 'LinePatternFill'
                    layer2.attrib['locked'] = '0'
                    properties = {
                        'color': ','.join([str(x) for x in lclass.symbol.color.rgba_8bit]),
                        'distance': '2',
                        'distance_unit': 'MM',
                        'line_width_unit': 'MM',
                        'lineangle': '45',
                        'linewidth': '0.26',
                        'offset': '0',
                        'offset_unit': 'MM',
                    }
                    for k,v in list(properties.items()):
                        prop = ET.SubElement(layer2, 'prop')
                        prop.attrib['k'] = k
                        prop.attrib['v'] = v

                    subsymbol = ET.SubElement(layer2, 'symbol')
                    subsymbol.attrib['alpha'] = '1'
                    subsymbol.attrib['type'] = 'line'

                    layer3 = ET.SubElement(subsymbol, 'layer')
                    layer3.attrib['pass'] = '0'
                    layer3.attrib['class'] = 'SimpleLine'
                    layer3.attrib['locked'] = '0'
                    properties = {
                        'capstyle': 'square',
                        'color': ','.join([str(x) for x in lclass.symbol.outlinecolor.rgba_8bit]),
                        'customdash': '5;2',
                        'customdash_unit': 'MM',
                        'joinstyle': 'bevel',
                        'offset': '0',
                        'offset_unit': 'MM',
                        'penstyle': 'solid',
                        'use_custom_dash': '0',
                        'width': str(lclass.symbol.outlinewidth*0.26),
                        'width_unit': 'MM',
                    }
                    for k,v in list(properties.items()):
                        prop = ET.SubElement(layer3, 'prop')
                        prop.attrib['k'] = k
                        prop.attrib['v'] = v

            n += 1

    indent(qgis)

    qml = '''<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n''' + ET.tostring(qgis).decode('utf-8')
    
    return qml

def indent(elem, level=0):
    '''
    Pretty formatting for xml.etree.ElementTree instances
    Source (public domain): http://effbot.org/zone/element-lib.htm#prettyprint
    '''
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert an ArcView 3.x Legend (AVL) to a QGIS legend (QML)')
    parser.add_argument('avl', nargs=1, help='Path to *.avl')
    parser.add_argument('-p', dest='stdout', action='store_const', const=True, default=False, help='Print to STDOUT instead of writing to file')
    parser.add_argument('-f', '--field', dest='field', nargs=1, required=False, default=[None], help='Manually override field name')
    parser.add_argument('--shp', nargs=1, required=False, default=[None], help='Path to *.shp, used for correcting field name case')
    args = parser.parse_args()

    # read avl file
    f = open(args.avl[0], 'r')
    data = f.read()
    f.close()

    # convert the avl to qml
    qml = avl2qml(data, shapefile=args.shp[0], field_name=args.field[0])

    # write output
    if args.stdout is False:
        filename = re.sub('\.avl', '.qml', args.avl[0], re.IGNORECASE)
        f = open(filename, 'wb')
        f.write(qml.encode('utf-8'))
        f.close()
    else:
        print(qml)
