#!/usr/bin/env python3
# %%
"""
File Name: gmsh_to_abaqus_inp.py
Created on: 2026/06/08
Author: Chen mingkai
github: chmtk@outlook.com
describe: gmsh生成的inp文件转换为abaqus能识别的inp文件
cites: 
"""

from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass

import argparse
import sys
import os
from InpExchange.Applications.GmshToAbaqus import GmshToAbaqus 

def main():
    parser = argparse.ArgumentParser(
        description="Gmsh to Abaqus INP Converter"
    )
    parser.add_argument("input_file", help="Input .inp file from Gmsh")
    parser.add_argument("-o", "--output", default="output_mesh.inp", help="Output .inp file for Abaqus")
    
    args = parser.parse_args()

    if not os.path.isfile(args.input_file):
        print(f"Error: File {args.input_file} not found.")
        sys.exit(1)

    try:
        # 这里需要替换为你实际加载 inp 文件的逻辑
        # 例如: model = GmshToAbaqus.from_file(args.input_file)
        model = GmshToAbaqus.from_file(args.input_file) 
        
        model.app(output_file=args.output)
        print(f"Conversion successful. Output saved to: {args.output}")
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()