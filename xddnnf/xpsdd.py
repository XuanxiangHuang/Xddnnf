#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   SDD Classifiers explainer
#   Author: Xuanxiang Huang
#
################################################################################
import resource
from copy import deepcopy
from pysdd.sdd import SddNode
from pysat.formula import IDPool
from pysat.solvers import Solver
################################################################################


class XpSdd(object):
    """
        Explaining SDD classifier.
    """
    def __init__(self, root: SddNode, verb=0):
        self.root = root
        self.nf = None          # num of features
        self.feats = None       # features
        self.domtype = None     # type of domain ('discrete', 'continuous')
        self.bfeats = None      # binarized features (grouped together)
        self.bflits = None      # literal of binarized feature (grouped together)
        self.lits = None        # literal converted from instance
        self.verbose = verb     # verbose level

    def parse_feature_map(self, map_file):
        """
            Parse a file mapping a tuple feature,operator,value to a Boolean literal of SDD.
            Format is feature:opterator1value(s)(operator2):literal index (>0 or <0).
            operator can be '=', '!=', set '{}', interval ')(]['.

            :param map_file: e.g. age:=12:1 which means literal x_1 denotes age = 12;
                            e.g. age:{10,11,13}:-2 which means literal -x_2 denotes age in {10,11,13};
                            e.g. age:[12,14):3 which means literal x_3 denotes 12<=age<14.
            :return: number of features and its binarized literals..
        """
        with open(map_file, 'r') as fp:
            lines = fp.readlines()
        # filtering out comment lines (those that start with '#')
        lines = list(filter(lambda l: (not (l.startswith('#') or l.strip() == '')), lines))

        feats = []
        bfeats = []
        bflits = []
        opt_prefix = ('=', '!=', '{', '[', '(')
        index = 0

        assert (lines[index].strip().startswith('NF:'))
        nf = int((lines[index].strip().split())[1])
        index += 1

        assert (lines[index].startswith('Type:'))
        index += 1

        domtype = lines[index].strip().split(',')
        for ele in domtype:
            assert ele in ('discrete', 'continuous')
        index += 1

        assert (lines[index].startswith('Map:'))
        index += 1

        while index < len(lines):
            feat_opt_val_lit = lines[index].strip().split(sep=':')
            dom = feat_opt_val_lit[:-1][-1]
            assert dom.startswith(opt_prefix)
            if dom.startswith('{'):
                assert dom.endswith('}')
            elif dom.startswith(('[', '(')):
                assert dom.endswith((']', ')'))

            if feat_opt_val_lit[0] not in feats:
                feats.append(feat_opt_val_lit[0])
                bfeats.append([tuple(feat_opt_val_lit[:-1])])
                bflits.append([int(feat_opt_val_lit[-1])])

            else:
                idx = feats.index(feat_opt_val_lit[0])
                bfeats[idx].append(tuple(feat_opt_val_lit[:-1]))
                bflits[idx].append(int(feat_opt_val_lit[-1]))

            index += 1

        assert len(feats) == nf
        assert len(bfeats) == nf
        assert len(bflits) == nf
        assert len(domtype) == nf

        self.nf = nf
        self.feats = feats
        self.domtype = domtype
        self.bfeats = bfeats
        self.bflits = bflits

        if self.verbose == 2:
            print(f"##### parse feature map #####")
            for f, v, l, dtype in zip(feats, bfeats, bflits, domtype):
                print(f"feat: {f}, val: {v}, lit: {l}, type: {dtype}")

    def parse_instance(self, inst):
        """
            Parse an instance to a list of literals
            and store. Note that this is MANDATORY
            before explaining an instance.

            :param inst: Given instance, e.g. [0,5,2,3]
            :return: None
        """
        assert (self.nf == len(inst))
        lits = []
        for j in range(self.nf):
            blits = []
            if self.domtype[j] == 'discrete':
                val_j = str(inst[j])
                for jj in range(len(self.bfeats[j])):
                    dom = self.bfeats[j][jj][1]
                    if dom.startswith('='):
                        if val_j == dom[1:]:
                            blits.append(self.bflits[j][jj])
                        else:
                            blits.append(-self.bflits[j][jj])
                    elif dom.startswith('!='):
                        if val_j != dom[2:]:
                            blits.append(self.bflits[j][jj])
                        else:
                            blits.append(-self.bflits[j][jj])
                    elif dom.startswith('{'):
                        if val_j in dom[1:-1].split(sep=','):
                            blits.append(self.bflits[j][jj])
                        else:
                            blits.append(-self.bflits[j][jj])
            else:
                val_j = float(inst[j])
                for jj in range(len(self.bfeats[j])):
                    bound = self.bfeats[j][jj][1].split(',')
                    lbound = float(bound[0][1:])
                    ubound = float(bound[1][:-1])
                    if bound[0].startswith('(') and bound[1].endswith(')') and lbound < val_j < ubound:
                        blits.append(self.bflits[j][jj])
                    elif bound[0].startswith('[') and bound[1].endswith(']') and lbound <= val_j <= ubound:
                        blits.append(self.bflits[j][jj])
                    elif bound[0].startswith('(') and bound[1].endswith(']') and lbound < val_j <= ubound:
                        blits.append(self.bflits[j][jj])
                    elif bound[0].startswith('[') and bound[1].endswith(')') and lbound <= val_j < ubound:
                        blits.append(self.bflits[j][jj])
                    else:
                        blits.append(-self.bflits[j][jj])

            # all literals are consistent.
            for ele in blits:
                assert -ele not in blits
            # no literal occur more than once
            tmp = list(set(blits))
            tmp.sort(key=abs)
            lits.append(tmp)

        assert len(lits) == self.nf

        self.lits = lits

    def get_predict(self):
        """
            Return prediction of lits (which corresponds to the given instance).

            :return:
        """
        out = self.root
        for lit in self.lits:
            if lit:
                for ele in lit:
                    out = out.condition(ele)
        assert out.is_true() or out.is_false()
        return True if out.is_true() else False

    def reachable(self, univ, pred):
        """
            Check if desired prediction/class is reachable.

            :param univ: list of universal features
            :param pred: desired prediction
            :return: True if reachable else False
        """
        lits_ = deepcopy(self.lits)
        for i in range(self.nf):
            if univ[i]:
                lits_[i] = None

        out = self.root
        for lit_ in lits_:
            if lit_:
                for ele in lit_:
                    out = out.condition(ele)
        if pred:
            return not out.is_false()
        else:
            return not out.is_true()

    def find_axp(self, fixed=None):
        """
            Compute one abductive explanation (Axp).

            :param fixed: a list of features declared as fixed.
            :return: one abductive explanation,
                        each element in the return Axp is a feature index.
        """
        time = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime + \
               resource.getrusage(resource.RUSAGE_SELF).ru_utime

        pred = self.get_predict()
        # get/create fix array
        if not fixed:
            fix = [True for _ in range(self.nf)]
        else:
            fix = fixed.copy()
        assert (len(fix) == self.nf)

        lits_ = deepcopy(self.lits)
        for i in range(self.nf):
            if not fix[i]:
                lits_[i] = None

        for i in range(self.nf):
            if fix[i]:
                fix[i] = not fix[i]
                lits_[i] = None
                out = self.root
                for lit_ in lits_:
                    if lit_:
                        for ele in lit_:
                            out = out.condition(ele)
                if (pred and not out.is_true()) or (not pred and not out.is_false()):
                    lits_[i] = self.lits[i]
                    fix[i] = not fix[i]

        axp = [i for i in range(self.nf) if fix[i]]

        time = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime + \
               resource.getrusage(resource.RUSAGE_SELF).ru_utime - time

        if self.verbose:
            if self.verbose == 1:
                print(f"Axp: {axp}")
            elif self.verbose == 2:
                print(f"Axp: {axp} ({[self.feats[i] for i in axp]})")
            print("Runtime: {0:.4f}".format(time))

        return axp

    def find_cxp(self, universal=None):
        """
            Compute one contrastive explanation (Cxp).

            :param universal: a list of features declared as universal.
            :return: one contrastive explanation,
                        each element in the return Cxp is a feature index.
        """
        time = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime + \
               resource.getrusage(resource.RUSAGE_SELF).ru_utime

        pred = self.get_predict()
        # get/create univ array
        if not universal:
            univ = [True for _ in range(self.nf)]
        else:
            univ = universal.copy()
        assert (len(univ) == self.nf)

        lits_ = deepcopy(self.lits)
        for i in range(self.nf):
            if univ[i]:
                lits_[i] = None

        for i in range(self.nf):
            if univ[i]:
                univ[i] = not univ[i]
                lits_[i] = self.lits[i]
                out = self.root
                for lit_ in lits_:
                    if lit_:
                        for ele in lit_:
                            out = out.condition(ele)
                if (pred and out.is_true()) or (not pred and out.is_false()):
                    lits_[i] = None
                    univ[i] = not univ[i]

        cxp = [i for i in range(self.nf) if univ[i]]

        time = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime + \
               resource.getrusage(resource.RUSAGE_SELF).ru_utime - time

        if self.verbose:
            if self.verbose == 1:
                print(f"Cxp: {cxp}")
            elif self.verbose == 2:
                print(f"Cxp: {cxp} ({[self.feats[i] for i in cxp]})")
            print("Runtime: {0:.4f}".format(time))

        return cxp

    def enum_exps(self):
        """
            Enumerate all (abductive and contrastive) explanations, using MARCO algorithm.
            :return: a list of all Axps, a list of all Cxps.
        """

        #########################################
        vpool = IDPool()

        def new_var(name):
            """
                Inner function,
                Find or new a PySAT variable.
                See PySat.

                :param name: name of variable
                :return: index of variable
            """
            return vpool.id(f'{name}')

        #########################################

        time = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime + \
               resource.getrusage(resource.RUSAGE_SELF).ru_utime

        pred = self.get_predict()

        num_axps = 0
        num_cxps = 0
        axps = []
        cxps = []

        for i in range(self.nf):
            new_var(f'u_{i}')
        # all features are fixed at the beginning
        univ = [False for _ in range(self.nf)]

        with Solver(name="glucose4") as slv:
            while slv.solve():
                # first model is empty
                model = slv.get_model()
                for lit in model:
                    name = vpool.obj(abs(lit)).split(sep='_')
                    univ[int(name[1])] = False if lit < 0 else True
                if self.reachable(univ, not pred):
                    cxp = self.find_cxp(univ)
                    slv.add_clause([-new_var(f'u_{i}') for i in cxp])
                    num_cxps += 1
                    cxps.append(cxp)
                else:
                    fix = [not i for i in univ]
                    axp = self.find_axp(fix)
                    slv.add_clause([new_var(f'u_{i}') for i in axp])
                    num_axps += 1
                    axps.append(axp)

        time = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime + \
               resource.getrusage(resource.RUSAGE_SELF).ru_utime - time

        print('#AXp:', num_axps)
        print('#CXp:', num_cxps)
        print("Runtime: {0:.4f}".format(time))

        return axps, cxps

    def check_one_axp(self, axp):
        """
            Check if given axp is a subset-minimal weak axp
            of instance.

            :param axp: given axp
            :return: true if it is subset-minimal weak axp, else false.
        """
        # get prediction of literals
        pred = self.get_predict()
        # get/create fix array
        fix = [False] * self.nf
        for i in axp:
            fix[i] = True
        lits_ = deepcopy(self.lits)
        for i in range(self.nf):
            if not fix[i]:
                lits_[i] = None
        # it is a weak AXp
        tmp = self.root
        for lit_ in lits_:
            if lit_:
                for ele in lit_:
                    tmp = tmp.condition(ele)
        if (pred and not tmp.is_true()) or (not pred and not tmp.is_false()):
            print(f'given axp {axp} is not a weak AXp')
            return False
        # it is subset-minimal
        for i in range(self.nf):
            if fix[i]:
                fix[i] = not fix[i]
                lits_[i] = None
                tmp = self.root
                for lit_ in lits_:
                    if lit_:
                        for ele in lit_:
                            tmp = tmp.condition(ele)
                if (pred and not tmp.is_true()) or (not pred and not tmp.is_false()):
                    lits_[i] = self.lits[i]
                    fix[i] = not fix[i]
                else:
                    print(f'given axp {axp} is not subset-minimal')
                    return False

        return True

    def check_one_cxp(self, cxp):
        """
            Check if given cxp is a subset-minimal weak cxp
            of instance.

            :param cxp: given cxp
            :return: true if it is subset-minimal weak cxp, else false.
        """
        # get prediction of literals
        pred = self.get_predict()
        # get/create univ array
        univ = [False] * self.nf
        for i in cxp:
            univ[i] = True
        lits_ = deepcopy(self.lits)
        for i in range(self.nf):
            if univ[i]:
                lits_[i] = None
        # it is a weak CXp
        tmp = self.root
        for lit_ in lits_:
            if lit_:
                for ele in lit_:
                    tmp = tmp.condition(ele)
        if (pred and tmp.is_true()) or (not pred and tmp.is_false()):
            print(f'given axp {cxp} is not a weak CXp')
            return False
        # it is subset-minimal
        for i in range(self.nf):
            if univ[i]:
                univ[i] = not univ[i]
                lits_[i] = self.lits[i]
                tmp = self.root
                for lit_ in lits_:
                    if lit_:
                        for ele in lit_:
                            tmp = tmp.condition(ele)
                if (pred and tmp.is_true()) or (not pred and tmp.is_false()):
                    lits_[i] = None
                    univ[i] = not univ[i]
                else:
                    print(f'given axp {cxp} is not subset-minimal')
                    return False

        return True