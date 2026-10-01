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
    def __init__(self, problem, placements): #dia ngejalanin ini setiap State dibuat, placements itu posisi semua kendaraan (termasuk yg diluar kapal)
        self.problem = problem
        self.placements = placements 
        self.occ = {} #occ -> occupancy, itu lebih ke nyatet kendaraan mana yang nempatin (awalnya kosong)
        self.weight = 0 
        self.fee = 0 #weight sama fee kan total awalnya 0 yes ges

        for vid, p in placements.items(): #vid -> vehicle id, p -> placement
            if p.placed: #kendaraan yg di kapal doang yg diitung
                v = problem.vehicles[vid]
                self.weight += v.weight
                self.fee += v.fee
                for c in problem.cells(vid, p):
                    self.occ[c] = vid #jadi misalnya ada kendaraan A di cell (1,1) maka occ[(1,1)] = A, jadi bisa ngecek cell mana aja yang udah ditempati kendaraan mana

    @property
    def value(self) -> int:
        return self.fee #biar gampang ngecek total fee dari state ini, jadi klo misalnya mau bandingin state A sama B tinggal liat A.value sama B.value aja

    def apply(self, move: Move) -> "State":
        new = dict(self.placements) #jadi klo misalnya mau apply move ke state ini, bikin placements baru dulu
        new.update(move.changes) #update placements baru pake perubahan dari move
        return State(self.problem, new) #bikin state baru pake placements baru
    #dict(self.placements) -> salin dict posisi
    #new.update(move.changes) -> timpa posisi kendaraan yang berubah, terus bikin State baru dari dict itu

    def inside_ids(self) -> List[str]: 
        return [i for i, p in self.placements.items() if p.placed] #buat ngecek kendaraan mana aja yang ada DI KAPALNYA
    def outside_ids(self) -> List[str]: 
        return [i for i, p in self.placements.items() if not p.placed] #buat ngecek kendaraan mana aja yang ada DI LUAR KAPALNYA, buat visualisasi yes yes

    def to_dict(self) -> dict:
        return {
            "value": self.fee,
            "total_weight": self.weight,
            "vehicles": {
                vid: {"x": p.x, "y": p.y, "orientation": p.orientation,
                      "inside": p.placed}
                for vid, p in self.placements.items()
            },
        }

class Problem:
    def __init__(self, ship: Ship, vehicles: List[Vehicle]):
        self.ship = ship
        self.vehicles = Dict[str, Vehicle] = {v.id: v for v in vehicles} #jadi misalnya ada kendaraan A sama B, self.vehicles = {"A": VehicleA, "B": VehicleB}], biar gampang cari kendaraannya dari idnya
        self.ids = [v.id for v in vehicles] #daftar id kendaraan

    @staticmethod
    def dims(v, orientation): #dimension
        return (v.w, v.l) if orientation == HORIZONTAL else (v.l, v.w) #jadi klo misalnya orientasinya horizontal, maka width sama lengthnya tetep, klo vertical maka width sama lengthnya dibalik soale posisinya kan kek dirotate juga

    def cells(self, v, p):
        dx, dy = self.dims(v, p.orientation) #ngecek dimensi kendaraan based on kek orientationnya
        for cx in range(p.x, p.x + dx): #ngecek cell mana aja yang ditempati kendaraan itu
            for cy in range(p.y, p.y + dy):
                yield (cx, cy) #jadi misalnya kendaraan A ada di (1,1) dengan dimensi 2x3, maka cells(A, p) bakal ngeyield (1,1), (1,2), (1,3), (2,1), (2,2), (2,3); kaya muntahin semua posisi yang bisa dia tempatin gitu

    def is_valid(self, state: State, change: Dict[str, Placement]) -> Optional[int]: #this is for kaya nilai state abis berubah and diterapin gitu, kalau ga valid dia none tp dihitungnya based on delta ga buat state baru supaya anuin neighbornya cephat
        ship = self.ship
        weight, fee = state.weight, state.fee #ambil total weight sama fee dari state sekarang
        new_cells = set() #buat nyatet cell baru yang ditempati kendaraan yang berubah
        for vid, p in change.items():
            v = self.vehicles[vid]
            if state.placements[vid].placed:
                weight -= v.weight #klo misalnya kendaraan itu sebelumnya udah di kapal, maka total weight sama fee dikurangin dulu
                fee -= v.fee
            if p.placed:
                weight += v.weight #klo misalnya kendaraan itu sekarang ditempatin di kapal, maka total weight sama fee ditambahin
                fee += v.fee
                dx, dy = self.dims(v, p.orientation) #ngecek dimensi kendaraan based on kek orientationnya
                if p.x < 0 or p.y < 0 or p.x + dx > ship.w or p.y + dy > ship.l: #ngecek klo misalnya kendaraan itu keluar dari kapal or not
                    return None
                for c in self.cells(v,p):
                    owner = state.occ.get(c) #ngecek cell itu udah ditempati kendaraan lain or not
                    if owner is not None and owner not in changes:
                        return None #overlap
                    if c in new_cells:
                        return None #overlap sama yang baru berubah
                    new_cells.add(c) #tambahin cell baru yang ditempati kendaraan yang berubah
        if weight > ship.max_capacity: #ngecek klo misalnya total weight melebihi kapasitas kapal
            return None
        return fee #klo valid, return total fee baru

#Ini buat cuman cek diakhir doang ada logic yang dilanggar apa ngga, kaya cek 1-1 kendaraan lambat sih tp kaya dipastiin benernya aja makanya keluarannya either True/False kan

    def feasible_neighbors(self, state: State) -> Iterator[Tuple[Move, int]]: # enum semua neighbor yang feasible + nilainya
        P = state.placements
        ids = self.ids

        #1. Swap
        for i in range (len(ids)):
            a = ids[i]
            pa = P[a]
            for j in range(i + 1, len(ids)):
                b = ids[j]
                pb = P[b]
                if not pa.placed and not pb.placed:
                    continue #Klo kendaraannya sama-sama diluar ngapain diswap juga
                ch = {
                    a: Placement(pb.x, pb.y, pa.orientation),
                    b: Placement(pa.x, pa.y, pb.orientation),
                }
    