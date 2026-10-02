#Disini kan sebenernya disuru 1 algoritma aja tapi gw mau cobain pake 2 variasi which is si Steepest Ascent & Sideways Move biar bisa dicompare nantinya yak

from __future__ import annotations

import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from define import Problem, State

@dataclass
class HillClimbingResult:
    algorithm: str
    seed: int
    initial_state: State
    final_state: State
    history: List[int] #index 0 = state awal, index i = setelah iterasi ke-i
    iterations: int
    sideways_moves: int #banyaknya langkah sampai berhenti
    neighbors_evaluated: int #total tetangga yang udah dicek
    duration: float
    stop_reason: str #biar ketrack aja
    max_sideways: int = 0

    @property
    def initial_value(self) -> int:
        return self.history[0]

    @property
    def final_value(self) -> int:
        return self.history[-1]

    def summary(self) -> dict:
        return{
            "algorithm": self.algorithm,
            "seed": self.seed,
            "initial_state": self.initial_state.to_dict(),
            "final_state": self.final_state.to_dict(),
            "initial_value": self.initial_value,
            "final_value": self.final_value,
            "history": self.history,
            "iterations": self.iterations,
            "sideways_moves": self.sideways_moves,
            "neighbors_evaluated": self.neighbors_evaluated,
            "duration_sec": round(self.duration, 4),
            "stop_reason": self.stop_reason,
            "max_sideways": self.max_sideways
        }

def _climb(problem: Problem, initial: State, rng: random.Random, name: str, max_sideways: int, max_iters: int, seed: int) -> HillClimbingResult:
    t0 = time.perf_counter()
    state = initial
    history = [state.value]
    sideways_streak = 0
    sideways_total = 0
    evaluated = 0
    stop_reason = "max_iterations"

    for _ in range(max_iters):
        cur = state.value
        best_val, best_move, n_best = None, None, 0

        for move, val in problem.feasible_neighbors(state):
            evaluated += 1
            if val < cur:
                continue #yang lebih not better sekip sajah
            if best_val is None or val > best_val:
                best_val, best_move, n_best = val, move, 1
            elif val == best_val:
                n_best += 1
                if rng.random() < 1.0/n_best: #randomly pick one of the best moves
                    best_move = move

        if best_val is not None and best_val > cur: # begini naik
            state = state.apply(best_move)
            sideways_streak = 0
        elif best_val is not None and best_val == cur: #nah ini sideways move
            if sideways_streak >= max_sideways:
                stop_reason = ("locak optimum" if max_sideways == 0 else "max_sideways_reached")
                break
            state = state.apply(best_move)
            sideways_streak += 1
            sideways_total += 1
        else: #ga ada yang lebih baik, berhenti
            stop_reason = "local_optimum"
            break
        history.append(state.value)

    return HillClimbingResult(
        algorithm = name, seed = seed, initial_state = initial, final_state = state,
        history = history, iterations = len(history)-1, sideways_moves = sideways_total, neighbors_evaluated = evaluated, duration = time.perf_counter() - t0, stop_reason = stop_reason, max_sideways = max_sideways,
    )

def steepest_ascent(problem: Problem, initial: State, seed: int = 0, max_iters: int = 10000) -> HillClimbingResult:
    return _climb(problem, initial, random.Random(seed), "steepest_ascent", max_sideways=0, max_iters=max_iters, seed=seed)

def sideways_move(problem: Problem, initial: State, seed: int = 0, max_sideways: int = 100, max_iters: int = 10000) -> HillClimbingResult:
    return _climb(problem, initial, random.Random(seed), f"sideways_move (max = {max_sideways})", max_sideways=max_sideways, max_iters=max_iters, seed=seed)

