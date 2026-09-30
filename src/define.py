from __future__ import annotations #supaya si tipe data boleh nyebut class yang belum selesai didefine
import json
import random #generator data and angka acak
from dataclasses import dataclass #biar gampang nganu data
from typing import Dict, Iterator, List, Optional, Tuple #buat penjelas aja sebenernya

HORIZONTAL = "Horizontal"
VERTICAL = "Vertical" 
#Konstanta buat horizontal and vertical aja si basically

@dataclass(frozen = True)
class Vehicle:
    id: str
    w: int
    l: int #w sama l itu buat dimensionsnya
    fee: int #ShippingFee -> biar ga panjang aje
    weight: int
    eta: int = 0 #nilai bawaannya 0 klo ga diisi, belum dipake sihh

@dataclass(frozen = True)
class Ship:
    w: int
    l: int
    max_capacity: int

@dataclass(frozen = True)
class Placement:
    x: Optional[int] = None
    y: Optional[int] = None
    orientation: str = HORIZONTAL #ini lebih ke placeholder ajah, jd klo naro Placement otomatis naro horizontal

    @property
    def placed(self) -> bool:
        return self.x is not None #kalau misalnya p.placed itu artinya udah dikapal, biar gausah nulis kaya is not None dan mikir dikapal/not gituloo 
#orientation masuk sini karena selama search kan bisa rubah-rubah gitu orientasinya (move kan bisa ubah orientasi) sedangkan kayaa vehiclenya kan tetap

@dataclass(frozen = True)
class Move:
    kind: str #bingung mau namain apa, intinya kaya tipe movenya mau tuker, mindahin, muterin
    changes: Dict[str, Placement]
    desc: str = "" #keterangan text ajah

class State:
    def __init__(self, problem, placements):
        self.problem = problem
        self.placements = placements
        self.occ = {}
        self.weight = 0
        self.fee = 0
