# avl2qml

Python module for converting ArcView 3.x Legends (.avl) to QGIS styles (.qml).

The code is very much in development. It has only had limited testing; as such there is a good chance it wont work with your data. Feedback and contributions welcome!

### Usage

Basic usage: ```python avl2qml.py arcviewlegend.avl > qgislegend.qml```

See ```python avl2qml.py --help``` for more information.

### Dependencies

The program optionally uses the `ogr` module to correct the case of the field name specified in the legend.

It has been tested with Python 2.7 and 3.3.

### Licence

Released under the GNU General Public Licence v2. See full text in 'LICENCE'.
