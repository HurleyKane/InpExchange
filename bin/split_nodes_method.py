#!/usr/bin/env python3
"""
File Name: split_nodes_method.py
Created on: 2026/06/10
Author: Chen mingkai
github: chmtk@outlook.com
describe: 对inp文件中的节点集进行分裂节点法处理，生成新的inp文件
cites:
"""

from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass

import argparse
import sys
import os
from InpExchange.Applications.SplitNodes import SplitNodesMethod

def main():
    parser = argparse.ArgumentParser(
        description="Split Nodes Method for Abaqus INP files"
    )
    parser.add_argument("input_file", help="Input .inp file")
    parser.add_argument("--nset", required=True, help="Name of the node set to split")
    parser.add_argument("--surface-nodes", type=int, required=True, help="Number of nodes per surface element (3 for 3-node, 4 for 4-node)")
    parser.add_argument("-o", "--output", default="output_split_node.inp", help="Output .inp file")

    args = parser.parse_args()

    if not os.path.isfile(args.input_file):
        print(f"Error: File {args.input_file} not found.")
        sys.exit(1)

    try:
        model = SplitNodesMethod.from_file(args.input_file)

        model.app(
            nset_name=args.nset,
            sur_ele_nodes_num=args.surface_nodes,
            output_file=args.output
        )
        print(f"Split nodes method successful. Output saved to: {args.output}")

    except Exception as e:
        print(f"Error during split nodes method: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
