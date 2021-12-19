#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Run
#   Author: Xuanxiang Huang
#
################################################################################
from __future__ import print_function
import sys,os,getopt
from pysdd.sdd import Vtree, SddManager
from xddnnf.xpsdd import XpSdd
from xddnnf.xpddnnf import XpdDnnf
################################################################################


def usage():
    """
        Prints usage message.
    """
    print('Usage:', os.path.basename(sys.argv[0]), '[options] -d sdd/d-DNNF [-t vtree_file] -m feature_map -i instance_file')
    print('Options:')
    print('        -a, --all        List all explanation')
    print('        -c, --classifier sdd or ddnnf classifier')
    print('        -g, --dag        Classifier file')
    print('        -h, --help')
    print('        -i, --inst       Instance file')
    print('        -m, --map        Feature map')
    print('        -t, --vtree      Vtree file (if given DAG is a SDD)')
    print('        -v, --verb       Be verbose (show comments)')
    print('        -x, --xtype      Explanation type')
    print('                         Available values: axp, cxp (default: axp)')


def parse_options():
    """
        Parses command-line options:
    """
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                   'ac:g:hi:m:t:vx:',
                                   ['all',
                                    'classifier='
                                    'dag='
                                    'help',
                                    'inst=',
                                    'map=',
                                    'vtree=',
                                    'verb',
                                    'xtype='])
    except getopt.GetoptError as err:
        sys.stderr.write(str(err).capitalize())
        usage()
        sys.exit(1)

    all_xp = False
    classifier = None
    dag = None
    inst = None
    fvmap = None
    vtree = None
    verb = 1
    xtype = 'axp'

    for opt, arg in opts:
        if opt in ('-a', '--all'):
            all_xp = True
        elif opt in ('-c', '--classifier'):
            classifier = arg
            if classifier not in ('sdd', 'ddnnf'):
                print('wrong parameter: -c (classifier)')
                sys.exit(1)
        elif opt in ('-g', '--dag'):
            dag = arg
        elif opt in ('-h', '--help'):
            usage()
            sys.exit(0)
        elif opt in ('-i', '--inst'):
            inst = arg
        elif opt in ('-m', '--map'):
            fvmap = arg
        elif opt in ('-t', '--vtree'):
            vtree = arg
        elif opt in ('-v', '--verb'):
            verb += 1
        elif opt in ('-x', '--xtype'):
            xtype = str(arg)
            if xtype not in ('axp', 'cxp'):
                print('wrong parameter: -x (xtype)')
                sys.exit(1)
        else:
            assert False, f'Unhandled option: {opt} {arg}'

    return all_xp, classifier, dag, vtree, inst, fvmap, verb, xtype


if __name__ == '__main__':

    all_xp, classifier, dag, vtree, inst, fvmap, verb, xtype = parse_options()

    if not dag or not inst or not fvmap:
        exit(0)

    explainer = None

    if classifier == 'sdd':
        # string to bytes
        sdd_file = bytes(dag, 'utf-8')
        vtree_file = bytes(vtree, 'utf-8')
        vtree = Vtree.from_file(vtree_file)
        sdd = SddManager.from_vtree(vtree)
        # Disable gc and minimization
        sdd.auto_gc_and_minimize_off()
        root = sdd.read_sdd_file(sdd_file)

        xpsdd = XpSdd(root, verb=1)
        xpsdd.parse_feature_map(fvmap)
        explainer = xpsdd
    else:
        xpddnnf = XpdDnnf.from_file(dag, verb=1)
        xpddnnf.parse_feature_map(fvmap)
        explainer = xpddnnf

    assert explainer

    with open(inst, 'r') as fp:
        lines = fp.readlines()
    lines = list(filter(lambda l: (not (l.startswith('#') or l.strip() == '')), lines))
    for idx, line in enumerate(lines):
        inst = line.strip().split(',')
        print(f'#{idx}-th instance {inst}')
        explainer.parse_instance(inst)
        if all_xp:
            print("list all XPs ...")
            axps, cxps = explainer.enum_exps()
        elif xtype == 'axp':
            print("find an axp ...")
            axp = explainer.find_axp()
        elif xtype == 'cxp':
            print("find a cxp ...")
            cxp = explainer.find_cxp()
    exit(0)