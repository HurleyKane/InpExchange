# %%
"""
File Name: test_read_abaqus_inp.py
Created on: 2026/06/10
Author: Chen mingkai
github: chmtk@outlook.com
describe: 
cites: 
"""

from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass

from InpExchange.InpReader import InpModel

inp_model = InpModel.from_file("Job-1.inp")
inp_model.write_inp("Job-1-output.inp")