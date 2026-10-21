from __future__ import annotations

import math
import random
import time
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from define import Placement, Move, HORIZONTAL, VERTICAL, Problem, State

@dataclass
class AnnealingResult:
    algorithm: str
    seed: int
    initial_state: State
    final_state: State
    last_state: State
    history: List[int] #nilai obj dari current selama proses SA
    best_history: List[int] #nilai terbaik yg udah ditemukan tiap iterasi
    temp_history: List[float] #suhu SA setiap iterasi
    exp_log: List[Tuple[int, int, float]] #mencatat nilai (3) untuk setiap perpindahan yang lebih buruk --> iterasi ke berapa, delta, probabilitas nerima perubahan tsb
    iterations: int
    accepted: int
    worse_accepted: int
    neighbors_evaluated: int
    stuck_count: int
    stuck_iters: List[int] #daftar iterasi ketika kejadian 
    stuck_window: int
    final_is_local_optimum: bool
    duration: float
    stop_reason: str
    init_temp: float
    cooling_rate: float
    stopping_temp: float

    @property
    def initial_value(self) -> int:
        return self.initial_state.value

    @property
    def final_value(self) -> int:
        return self.final_state.value

def pick_neighbor(problem: Problem, state: State, rng: random.Random) -> Optional[Tuple[Move,int]]:
    for _ in range(100):
        category=rng.choice(["Rotate","Move", "Swap"])

        if category == "Rotate":
            vid=rng.choice(problem.ids)
            v=problem.vehicles[vid]
            if v.w == v.l:
                continue
            p=state.placements[vid]
            new=VERTICAL if p.orientation == HORIZONTAL else HORIZONTAL
            ch = {vid: Placement(p.x, p.y, new)}
            desc = f"Rotate {vid} --> {new}"

        elif category == "Move":
            vid  = rng.choice(problem.ids)
            v = problem.vehicles[vid]
            p = state.placements[vid]
            if p.placed and rng.random() < 0.2: 
                ch = {vid: Placement(None,None, p.orientation)}
                desc = f"Move {vid} out"
            else:
                dx,dy = problem.dims(v, p.orientation)
                if dx > problem.ship.w or dy > problem.ship.l:
                    continue
                x= rng.randint(0, problem.ship.w-dx)
                y= rng.randint(0, problem.ship.l-dy)
                ch= {vid: Placement(x,y, p.orientation)}
                desc=f"Move {vid} to ({x},{y})"

        else: #swap
            if len(problem.ids) < 2:
                continue
            a,b = rng.sample(problem.ids,2)
            pa,pb = state.placements[a], state.placements[b]
            if not pa.placed and not pb.placed:
                continue
            ch ={ a: Placement(pb.x, pb.y, pa.orientation), b: Placement(pa.x, pa.y, pb.orientation)}
            desc = f"Swap {a} and {b}"

        value= problem.evaluate(state, ch)

        if value is not None:
            return Move(category,ch, desc), value
    return None

def is_local_optimum(problem: Problem, state: State) -> bool:
    #kondisi true jika ga ada tetangga yang value nya lebih baik dari current
    cur= state.value

    for move, val in problem.feasible_neighbors(state):
        if val > cur:
            return False

    return True

def simulated_annealing(problem: Problem, initial: State, seed: int = 0, init_temp: float = 50.0, cooling_rate: float = 0.999, stopping_temp: float = 0.01, stuck_window: int = 50, trace: list | None = None) -> AnnealingResult:

    if not (0 < cooling_rate < 1):
        raise ValueError("cooling_rate harus di antara 0 dan 1")
    
    if stopping_temp <= 0 or init_temp <= stopping_temp:
        raise ValueError("stopping_temp harus > 0 dan lebih kecil dari init_temp")
    
    start = time.time()
    rng = random.Random(seed)
    current = initial
    best = initial

    if trace is not None:
        trace.append((0,best))

    T = init_temp

    iteration = 0
    consec_no_improve = 0

    stuck_count = 0
    stuck_iters = []
    stuck_checked = False #sudah dicek local optimum untuk part stagnan?

    best_hist = [] #mencatat value terbaik di setiap iterasi
    current_hist = [] #mencatat nilai state di setiap iterasi
    exp_hist = [] #mencatat nilai e^(delta/T) untuk move yang lebih buruk
    temp_hist = [] #mencatat suhu pada setiap iterasi

    accepted = 0
    worse_accepted = 0
    neighbors_evaluated = 0

    while T > stopping_temp:
        iteration += 1
        value_before = current.value
        neighbor = pick_neighbor(problem, current, rng)

        if neighbor is not None:
            move, neighbor_value =  neighbor
            neighbors_evaluated += 1
            delta = neighbor_value - current.value

            if delta > 0:
                probability = 1.0
            else:
                probability = math.exp(delta/T)
                if delta < 0:
                    exp_hist.append((iteration,delta,probability)) #hanya move yang lebih buruk

            if delta > 0 or rng.random() < probability:
                current = current.apply(move)
                accepted += 1

                if delta < 0:
                    worse_accepted += 1

                if current.value > best.value:
                    best = current
                    if trace is not None:                      
                        trace.append((iteration, best)) 

        #cek stagnan
        if current.value != value_before:
            consec_no_improve = 0
            stuck_checked = False
        else:
            consec_no_improve += 1

        if consec_no_improve >= stuck_window and not stuck_checked:
            stuck_checked = True #cek sekali per episode stagnan (is_local_optimum mahal)
            if is_local_optimum(problem, current):
                stuck_count += 1
                stuck_iters.append(iteration)

        current_hist.append(current.value)
        best_hist.append(best.value)
        temp_hist.append(T)    

        T *= cooling_rate

    duration = time.time() - start

    return AnnealingResult(
        algorithm="Simulated Annealing", seed=seed, initial_state=initial, final_state=best, last_state=current,
        history=current_hist, best_history=best_hist, temp_history=temp_hist, exp_log=exp_hist, iterations=iteration,
        accepted=accepted, worse_accepted=worse_accepted, neighbors_evaluated=neighbors_evaluated, stuck_count=stuck_count,
        stuck_iters=stuck_iters, stuck_window=stuck_window, final_is_local_optimum=is_local_optimum(problem, best),
        duration=duration, stop_reason="min_temp", init_temp=init_temp, cooling_rate=cooling_rate, stopping_temp=stopping_temp
    )