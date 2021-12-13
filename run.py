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
################################################################################


def checkMHS(in_axps: list, in_cxps: list):
    # given a list of axp and a list of cxp,
    # check if they are minimal-hitting-set (MHS) of each other
    # 1. uniqueness, and no subset(superset) exists;
    if not in_axps or not in_cxps:
        print(f"input empty: {in_axps}, {in_cxps}")
        return False
    axps = sorted(in_axps, key=lambda x: len(x))
    axps_ = axps[:]
    while axps:
        axp = axps.pop()
        set_axp = set(axp)
        for ele in axps:
            set_ele = set(ele)
            if set_axp.issuperset(set_ele) or set_axp.issubset(set_ele):
                print(f"axp is not unique: {set_axp}, {set_ele}")
                return False
    cxps = sorted(in_cxps, key=lambda x: len(x))
    cxps_ = cxps[:]
    while cxps:
        cxp = cxps.pop()
        set_cxp = set(cxp)
        for ele in cxps:
            set_ele = set(ele)
            if set_cxp.issuperset(set_ele) or set_cxp.issubset(set_ele):
                print(f"cxp is not unique: {set_cxp}, {set_ele}")
                return False
    # 2. minimal hitting set;
    for axp in axps_:
        set_axp = set(axp)
        for cxp in cxps_:
            set_cxp = set(cxp)
            if not (set_axp & set_cxp):  # not a hitting set
                print(f"not a hitting set: axp:{set_axp}, cxp:{set_cxp}")
                return False
    # axp is a MHS of cxps
    for axp in axps_:
        set_axp = set(axp)
        for ele in set_axp:
            tmp = set_axp - {ele}
            size = len(cxps_)
            for cxp in cxps_:
                set_cxp = set(cxp)
                if tmp & set_cxp:
                    size -= 1
            if size == 0:  # not minimal
                print(f"axp is not minimal hitting set: "
                      f"axp {set_axp} covers #{len(cxps_)}, "
                      f"its subset {tmp} covers #{len(cxps_) - size}, "
                      f"so {ele} is redundant")
                return False
    # cxp is a MHS of axps
    for cxp in cxps_:
        set_cxp = set(cxp)
        for ele in set_cxp:
            tmp = set_cxp - {ele}
            size = len(axps_)
            for axp in axps_:
                set_axp = set(axp)
                if tmp & set_axp:
                    size -= 1
            if size == 0:
                print(f"cxp is not minimal hitting set: "
                      f"cxp {set_cxp} covers #{len(axps_)}, "
                      f"its subset {tmp} covers #{len(axps_) - size}, "
                      f"so {ele} is redundant")
                return False
    return True


def usage():
    """
        Prints usage message.
    """
    print('Usage:', os.path.basename(sys.argv[0]), '[options] -d sdd/d-DNNF [-t vtree_file] -m feature_map -i instance_file')
    print('Example: ./run.py -c sdd -g examples/xd6/xd6.txt -t examples/xd6/xd6_vtree.txt '
          '-m examples/xd6/xd6_map.txt -i examples/xd6/xd6_inst.csv -x axp')
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

        with open(inst, 'r') as fp:
            lines = fp.readlines()
        lines = list(filter(lambda l: (not (l.startswith('#') or l.strip() == '')), lines))
        for idx, line in enumerate(lines):
            inst = line.strip().split(',')
            print(f'#{idx}-th instance {inst}')
            xpsdd.parse_instance(inst)
            if all_xp:
                print("list all XPs ...")
                axps, cxps = xpsdd.enum_exps()
                # check each axp and cxp
                for item in axps:
                    assert xpsdd.check_one_axp(item)
                for item in cxps:
                    assert xpsdd.check_one_cxp(item)
                # assert axps are MHS of cxps, vice versa
                assert checkMHS(axps, cxps)
            elif xtype == 'axp':
                print("find an axp ...")
                axp = xpsdd.find_axp()
                assert xpsdd.check_one_axp(axp)
            elif xtype == 'cxp':
                print("find a cxp ...")
                cxp = xpsdd.find_cxp()
                assert xpsdd.check_one_cxp(cxp)
    else:
        print("haven't implemented")
        exit()

    exit(0)