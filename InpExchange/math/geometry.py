# %%
"""
File Name: geometry.py
Created on: 2026/06/09
Author: Chen mingkai
github: chmtk@outlook.com
describe: 
cites: 
"""

from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass

import numpy as np

def angle_to_z_axis(n):
    """
    计算法向量旋转到 Z 轴正方向的夹角（度数）和旋转方向（XY平面投影）
    
    Parameters
    ----------
    n : array_like, shape (3,)
        单位法向量
    
    Returns
    -------
    theta_deg : float
        与 Z 轴正方向的夹角，0-180 度
    rot_dir : str
        XY平面旋转方向，'CCW' 或 'CW' （逆时针counterclockwise 顺时针clockwise）
    """
    n = np.asarray(n, dtype=float)
    n /= np.linalg.norm(n)
    
    # 与 Z 轴夹角
    theta = np.arccos(np.clip(n[2], -1.0, 1.0))
    theta_deg = np.degrees(theta)
    
    # XY 投影旋转方向
    nx, ny = n[0], n[1]
    if nx == 0 and ny == 0:
        rot_dir = "None"  # 已经在 Z 轴上
    else:
        angle_xy = np.arctan2(ny, nx)
        rot_dir = "CCW" if angle_xy > 0 else "CW"
    
    return theta_deg, rot_dir


def face_normal(p1, p2, p3):
    """
    计算三点形成平面的法向量
    - 三维空间：返回两个方向的单位法向量，并按 (x,y,z) 排序
    - 二维平面（平行于 xy）：返回 z 方向法向量 ±1
    
    Parameters
    ----------
    p1, p2, p3 : array_like, shape (3,)
    
    Returns
    -------
    n1, n2 : ndarray, shape (3,)
        两个方向相反的单位法向量
    """
    p1 = np.asarray(p1, dtype=float)
    p2 = np.asarray(p2, dtype=float)
    p3 = np.asarray(p3, dtype=float)
    
    # 判断是否在二维平面（xy平面）: z 均相等
    if np.allclose(p1[2], p2[2]) and np.allclose(p1[2], p3[2]):
        # 取 z 方向
        n1 = np.array([0, 0, 1])
        n2 = np.array([0, 0, -1])
        normals = [n2, n1]  # 按 x,y,z 排序
        return normals[0], normals[1]
    
    # 三维情况
    v1 = p2 - p1
    v2 = p3 - p1
    n = np.cross(v1, v2)
    norm = np.linalg.norm(n)
    
    if norm < 1e-12:
        raise ValueError("三点共线，无法确定法向量")
    
    n = n / norm
    return n

import numpy as np


def point_plane_side(point, plane_point, normal, tol=1e-10):
    """
    判断点位于平面法向量哪一侧

    Returns
    -------
    1  : 法向量方向
    -1 : 法向量反方向
    0  : 在平面上
    """
    point = np.asarray(point, dtype=float)
    plane_point = np.asarray(plane_point, dtype=float)
    normal = np.asarray(normal, dtype=float)

    try:
        d = np.dot(point - plane_point, normal)
    except Exception as e:
        pass

    if d > tol:
        return 1
    elif d < -tol:
        return -1
    else:
        return 0

if __name__ == "__main__":
    # p1 = [0, 0, 0]
    # p2 = [1, 0, 0]
    # p3 = [0, 1, 1]

    # n1, n2 = face_normal(p1, p2, p3)
    n1 = [-1, -0, -0]
    n2 = [1, 0, 0]
    print(n1, n2)

    theta, rot = angle_to_z_axis(n1)
    print(f"夹角: {theta:.2f} 度, 旋转方向: {rot}")  
    theta, rot = angle_to_z_axis(n2) 
    print(f"夹角: {theta:.2f} 度, 旋转方向: {rot}")  