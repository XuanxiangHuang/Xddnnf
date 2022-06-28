# Xddnnf
A Python package for explaining d-DNNF/SDD classifiers.

## Getting Started
To run scripts, you need:
- [PySAT](https://github.com/pysathq/pysat)
- [PySDD](https://github.com/wannesm/PySDD)


## Usage

```
python3 run.py -h
```

## Example

```
python3 run.py -c sdd -g examples/xd6/sdd/xd6.sdd -t examples/xd6/sdd/xd6.vtree -m examples/xd6/xd6.map -i examples/xd6/xd6_inst.csv -x axp
python3 run.py -c ddnnf -g examples/german/ddnnf/german.dnnf -m examples/german/german.map -i examples/german/german_inst.csv -x cxp
```

## Citation

If you make use of this code in your own work, please cite our paper:
```
@article{huang2022tractable,
  title={Tractable explanations for d-DNNF classifiers},
  author={Huang, Xuanxiang and Izza, Yacine and Ignatiev, Alexey and Cooper, MC and Asher, Nicholas and Marques-Silva, Joao},
  journal={AAAI, February},
  year={2022}
}
```