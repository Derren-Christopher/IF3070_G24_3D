from __future__ import annotations #disini kita bs nyebutin nama kelas yang belom di definisikan
import random
import sys #buat path import
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from define import HORIZONTAL, VERTICAL, Move, Placement, Problem, State


# peluang tiap jenis mutasi (total = 1.0)
MUTATION_WEIGHTS = {"Swap": 0.27, "Move": 0.53, "Rotate": 0.20}




@dataclass
class GeneticResult:
    algorithm: str
    seed: int
    population_size: int #jumlah individu tiap generasi
    generations: int #banyak iterasi (1 iterasi = 1 generasi)
    initial_state: State #individu terbaik di populasi awal
    final_state: State #individu terbaik sepanjang pencarian
    history_best: List[int] #index 0 = populasi awal, index i = setelah generasi ke-i
    history_avg: List[float] #rata2 nilai populasi, indexnya sama kayak history_best
    duration: float
    params: dict #parameter yang dipake utk dicatat


    @property
    def initial_value(self) -> int:
        return self.initial_state.value #nilai state awal


    @property
    def final_value(self) -> int:
        return self.final_state.value #nilai state akhir


    @property
    def iterations(self) -> int:
        return self.generations #menyamakan dengan algoritma lain biar bisa dibandingin


    def summary(self) -> dict: #biar disimpen sebagai json
        return {
            "algorithm": self.algorithm,
            "seed": self.seed,
            "population_size": self.population_size,
            "generations": self.generations,
            "params": self.params,
            "initial_state": self.initial_state.to_dict(),
            "final_state": self.final_state.to_dict(),
            "initial_value": self.initial_value,
            "final_value": self.final_value,
            "iterations": self.iterations,
            "history": self.history_best,
            "history_avg": [round(a, 3) for a in self.history_avg],
            "duration_sec": round(self.duration, 4),
        }




def random_selection(population: List[State], rng: random.Random, k: int) -> State:
    #ambil k individu acak, yang nilainya paling gede jadi induk
    contestants = rng.sample(population, min(k, len(population))) #ambil k acak, jangan lebih dari isi populasi
    return max(contestants, key=lambda s: s.value) #yang value-nya paling tinggi menang




def crossover(problem: Problem, a: State, b: State, rng: random.Random) -> State:
    #gabungin 2 induk jadi 1 anak, anaknya pasti valid (ga numpuk, ga keluar kapal, ga overweight)
    #geladak dipotong 1 garis, sisi kiri dari satu induk, sisi kanan dari induk satunya
    ship = problem.ship
    sumbu_ok = [s for s, n in ((0, ship.w), (1, ship.l)) if n >= 2] #sumbu yang cukup panjang buat dipotong
    if not sumbu_ok: #kapal 1x1, ga bisa dipotong
        return a
    sumbu = rng.choice(sumbu_ok) #0 = potong di lebar (x), 1 = potong di panjang (y)
    batas = ship.w if sumbu == 0 else ship.l #panjang sumbu yang dipotong
    garis = rng.randint(1, batas - 1) #posisi garis potong
    kiri, kanan = (a, b) if rng.random() < 0.5 else (b, a) #acak induk mana yang dapet sisi kiri


    candidates = []  # kendaraan yang mau diwariskan ke anak
    for vehicle_id in problem.ids:
        vehicle = problem.vehicles[vehicle_id]
        left_position = kiri.placements[vehicle_id]
        if left_position.placed:
            dx, dy = problem.dims(vehicle, left_position.orientation)
            end_position = left_position.x + dx if sumbu == 0 else left_position.y + dy
            if end_position <= garis:  # kendaraan utuh di sisi kiri garis
                candidates.append((vehicle_id, left_position))
        right_position = kanan.placements[vehicle_id]
        if right_position.placed:
            start_position = right_position.x if sumbu == 0 else right_position.y
            if start_position >= garis:  # kendaraan utuh di sisi kanan garis
                candidates.append((vehicle_id, right_position))


    rng.shuffle(candidates)  # acak urutan kandidat
    candidates.sort(key=lambda c: problem.vehicles[c[0]].fee, reverse=True)  # fee terbesar dicoba duluan


    placements = {}  # placement anak, vehicle_id -> Placement
    occupied_cells = set()  # geladak yang sudah dipakai anak
    total_weight = 0  # total berat kendaraan di anak


    def add_vehicle(vehicle_id, placement):
        # Coba menaruh kendaraan di posisi placement.
        nonlocal total_weight
        if vehicle_id in placements or not placement.placed:
            return False
        vehicle = problem.vehicles[vehicle_id]
        if total_weight + vehicle.weight > ship.max_capacity:
            return False
        dx, dy = problem.dims(vehicle, placement.orientation)
        if (placement.x < 0 or placement.y < 0
                or placement.x + dx > ship.w or placement.y + dy > ship.l):
            return False
        cells = list(problem.cells(vehicle, placement))
        if any(cell in occupied_cells for cell in cells):
            return False
        occupied_cells.update(cells)
        total_weight += vehicle.weight
        placements[vehicle_id] = placement
        return True


    for vehicle_id, placement in candidates:
        add_vehicle(vehicle_id, placement)


    remaining = [vid for vid in problem.ids if vid not in placements]
    rng.shuffle(remaining)
    remaining.sort(key=lambda vid: problem.vehicles[vid].fee, reverse=True)
    for vehicle_id in remaining:
        for parent in (a, b):
            placement = parent.placements[vehicle_id]
            if placement.placed and add_vehicle(vehicle_id, placement):
                break


    result_placements = {}
    for vehicle_id in problem.ids:
        if vehicle_id in placements:
            result_placements[vehicle_id] = placements[vehicle_id]
        else:
            result_placements[vehicle_id] = Placement(
                None, None, rng.choice((a, b)).placements[vehicle_id].orientation)
    return State(problem, result_placements)




def mutate(problem: Problem, state: State, rng: random.Random, tries: int = 30) -> State:
    #satu perubahan kecil acak yang valid, jenisnya sama kayak move buat neighbor di spek
    ids = problem.ids
    jenis_list = list(MUTATION_WEIGHTS)
    bobot = list(MUTATION_WEIGHTS.values())
    for _ in range(tries): #coba MAX 30x
        jenis = rng.choices(jenis_list, weights=bobot)[0] #acak jenis mutasi
        if jenis == "Swap": #tukar posisi 2 kendaraan
            a, b = rng.sample(ids, 2) #ambil 2 kendaraan beda
            pa, pb = state.placements[a], state.placements[b]
            if not pa.placed and not pb.placed: #dua2nya di luar, ditukar juga ga ngaruh
                continue
            ch = {a: Placement(pb.x, pb.y, pa.orientation), b: Placement(pa.x, pa.y, pb.orientation)} #saling ambil posisi
        elif jenis == "Move": #pindahin kendaraan ke koordinat lain
            vid = rng.choice(ids)
            p = state.placements[vid]
            if p.placed and rng.random() < 0.1: #10% kendaraan yang di dalem dikeluarin
                ch = {vid: Placement(None, None, p.orientation)}
            else:
                o = p.orientation if p.placed else rng.choice([HORIZONTAL, VERTICAL]) #yang di luar boleh masuk dengan orientasi apa aja
                dx, dy = problem.dims(problem.vehicles[vid], o)
                if dx > problem.ship.w or dy > problem.ship.l: #kendaraannya kegedean buat kapal
                    continue
                ch = {vid: Placement(rng.randint(0, problem.ship.w - dx), rng.randint(0, problem.ship.l - dy), o)} #koordinat acak yang masih di dalem kapal
        else: #Rotate, ubah orientasi
            dalam = [i for i in ids if state.placements[i].placed and problem.vehicles[i].w != problem.vehicles[i].l] #yang di kapal dan bukan persegi
            if not dalam:
                continue
            vid = rng.choice(dalam)
            p = state.placements[vid]
            o = VERTICAL if p.orientation == HORIZONTAL else HORIZONTAL #dibalik
            ch = {vid: Placement(p.x, p.y, o)}
        if problem.evaluate(state, ch) is not None: #valid kalo ga None
            return state.apply(Move(jenis, ch)) #terapin, jadi state baru
    return state #ga nemu perubahan yang valid, state dibalikin apa adanya




def genetic_algorithm(
    problem: Problem,
    population_size: int = 50, #jumlah individu per generasi
    generations: int = 300, #banyak iterasi
    seed: int = 0, #biar hasil bisa diulang
    crossover_rate: float = 0.9, #peluang 2 induk di-crossover
    mutation_rate: float = 0.9, #peluang anak dimutasi
    mutation_steps: int = 6, #maksimal berapa kali mutasi per anak
    elite_size: int = 2, #berapa individu terbaik yang langsung lolos
    tournament_k: int = 2, #ukuran turnamen
    init_attempts: int = 40, #berapa kali nyoba naro kendaraan pas bikin state awal
) -> GeneticResult:
    t0 = time.perf_counter() #mulai itung durasi
    rng = random.Random(seed) #generator acak sendiri, seed sama = hasil sama
    populasi = [problem.random_state(rng, attempts=init_attempts) for _ in range(population_size)] #populasi awal, semuanya state random yang valid
    terbaik = max(populasi, key=lambda s: s.value) #yang paling bagus di populasi awal
    awal = terbaik #disimpen buat initial_state
    history_best = [terbaik.value] #index 0 = populasi awal
    history_avg = [sum(s.value for s in populasi) / len(populasi)]
    elite_size = min(elite_size, population_size) #jangan lebih dari isi populasi


    for _ in range(generations): #1 putaran = 1 generasi = 1 iterasi
        urut = sorted(populasi, key=lambda s: s.value, reverse=True) #urut dari nilai tertinggi
        baru = urut[:elite_size] #elitism, yang paling bagus langsung lolos
        while len(baru) < population_size: #sisanya diisi anak
            p1 = random_selection(populasi, rng, tournament_k) #induk 1
            p2 = random_selection(populasi, rng, tournament_k) #induk 2
            anak = crossover(problem, p1, p2, rng) if rng.random() < crossover_rate else p1 #kadang ga crossover, anaknya copy induk 1
            if rng.random() < mutation_rate: #kadang dimutasi
                for _ in range(rng.randint(1, mutation_steps)): #1 sampai mutation_steps kali
                    anak = mutate(problem, anak, rng)
            baru.append(anak)
        populasi = baru #generasi baru gantiin yang lama
        terbaik_gen = max(populasi, key=lambda s: s.value) #terbaik di generasi ini
        if terbaik_gen.value > terbaik.value: #kalo lebih bagus dari yang pernah ada
            terbaik = terbaik_gen
        history_best.append(terbaik.value) #nilai terbaik sepanjang pencarian, ga pernah turun
        history_avg.append(sum(s.value for s in populasi) / len(populasi))


    return GeneticResult(
        algorithm="genetic_algorithm", seed=seed, population_size=population_size,
        generations=generations, initial_state=awal, final_state=terbaik,
        history_best=history_best, history_avg=history_avg,
        duration=time.perf_counter() - t0,
        params={"crossover_rate": crossover_rate, "mutation_rate": mutation_rate,
                "mutation_steps": mutation_steps, "elite_size": elite_size,
                "tournament_k": tournament_k, "init_attempts": init_attempts,
                "mutation_weights": dict(MUTATION_WEIGHTS)},
    )