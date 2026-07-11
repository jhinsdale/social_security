#!/usr/bin/python

from __future__ import print_function
import os
import sys
from xml.etree import ElementTree

def children(node):
    if not hasattr(node, "_children"):
        return []
    return node._children

def get_elt(node):
    tag = node.tag
    atts = node.attrib
    if '}' in tag:
        tag = tag[tag.index('}')+1:]
    return tag, atts, node.text, children(node)

def main(args):

    if len(args) != 1:
        print('Usage: format_ssa.py <XMLfile>')
        return False
    
    xmlfn = args[0]
    assert os.path.isfile(xmlfn), 'Cannot find "{}"'.format(xmlfn)
    tree = ElementTree.parse(xmlfn)
    root = tree.getroot()
    data = {}
    for section in root:
        tag, atts, text, children = get_elt(section)
        if tag == 'FileCreationDate':
            data['FileCreationDate'] = text
        elif tag == 'UserInformation':
            u = data['UserInformation'] = {}
            for celt in children:
                c_tag, c_atts, c_text, c_children = get_elt(celt)
                u[c_tag] = c_text
        elif tag == 'EstimatedBenefits':
            e = data['EstimatedBenefits'] = {}
            for celt in children:
                c_tag, c_atts, c_text, c_children = get_elt(celt)
                if c_children:
                    est_age, est_estimate = None, None
                    for ec_elt in c_children:
                        ec_tag, ec_atts, ec_text, ec_children = get_elt(ec_elt)
                        if ec_tag == 'RetirementAge':
                            ecy_elt = ec_children[0]
                            ecy_tag, ecy_atts, ecy_text, ecy_children = get_elt(ecy_elt)
                            assert ecy_tag == 'Years'
                            assert not ecy_children
                            est_age = int(ecy_text)
                        elif ec_tag == 'Estimate':
                            est_estimate = int(ec_text)
                        else:
                            raise ValueError('Unexpected tag "{}" under {}/{}'.format(ec_tag, tag, c_tag))
                    e[c_tag] = (est_age, est_estimate)
                else:
                    e[c_tag] = int(c_text)
        elif tag == 'EarningsRecord':
            pass
        else:
            raise ValueError('Unknown tag "{}"'.format(tag))

    import pprint
    pprint.pprint(data)
    return True

if __name__ == '__main__':
    success = main(sys.argv[1:])
    sys.exit(0 if success else 1)
