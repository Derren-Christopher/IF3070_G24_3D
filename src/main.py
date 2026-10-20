from __future__ import annotations

import random

from define import HORIZONTAL, VERTICAL, Placement, Problem, Ship, State, Vehicle, generate_problem
from hill_climbing import HillClimbingResult, sideways_move, steepest_ascent


def ask_int(prompt: str, minimum: int = 0) -> int:
    while True:
        try:
            value = int(input(prompt))
            if value >= minimum:
                return value
            print(f"Nilai harus >= {minimum}.")
        except ValueError:
            print("Input harus angka bulat.")


def ask_choice(prompt: str, options: list[str]) -> str:
    while True:
        value = input(prompt).strip().upper()
        if value in [opt.upper() for opt in options]:
            return value
        print(f"Pilih salah satu: {', '.join(options)}")


def ask_yes_no(prompt: str) -> bool:
    while True:
        value = input(prompt).strip().lower()
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Jawab y/yes atau n/no.")


def user_placement(problem: Problem) -> State:
    placements: dict[str, Placement] = {}
    print("\nMasukkan placement awal tiap kendaraan.")
    for vid in problem.ids:
        if ask_yes_no(f"{vid} masuk kapal? (y/n): "):
            orientation = ask_choice(f"Orientasi {vid} ({HORIZONTAL}/{VERTICAL})? ", [HORIZONTAL, VERTICAL])
            x = ask_int(f"x {vid}: ", 0)
            y = ask_int(f"y {vid}: ", 0)
            placements[vid] = Placement(x, y, orientation.capitalize())
        else:
            orientation = ask_choice(f"Orientasi default {vid} saat di luar kapal ({HORIZONTAL}/{VERTICAL})? ", [HORIZONTAL, VERTICAL])
            placements[vid] = Placement(None, None, orientation.capitalize())
    return State(problem, placements)


def build_manual_vehicles(n_vehicles: int) -> list[Vehicle]:
    vehicles: list[Vehicle] = []
    print("\nMasukkan data kendaraan secara manual.")
    for i in range(1, n_vehicles + 1):
        print(f"\nKendaraan {i}")
        w = ask_int(f"  Lebar kendaraan {i}: ", 1)
        l = ask_int(f"  Panjang kendaraan {i}: ", 1)
        fee = ask_int(f"  Fee kendaraan {i}: ", 0)
        weight = ask_int(f"  Berat kendaraan {i}: ", 0)
        eta = ask_int(f"  ETA kendaraan {i}: ", 0)
        vehicles.append(Vehicle(f"V{i:02d}", w, l, fee, weight, eta))
    return vehicles


def random_state(problem: Problem, seed: int = 0) -> State:
    rng = random.Random(seed)
    return problem.random_state(rng, attempts=40)


def print_vehicle_list(problem: Problem) -> None:
    print("\n=== Daftar kendaraan yang dibuat ===")
    for v in problem.vehicles.values():
        print(f"- {v.id}: ukuran={v.w}x{v.l}, fee={v.fee}, weight={v.weight}, eta={v.eta}")


def print_vehicle_positions(state: State, title: str) -> None:
    print(f"\n=== {title} ===")
    print(f"Value (total fee): {state.value} | Total berat: {state.weight} / {state.problem.ship.max_capacity}")
    for vid, p in state.placements.items():
        if p.placed:
            print(f"- {vid}: DI DALAM  (x={p.x}, y={p.y}, orientation={p.orientation})")
        else:
            print(f"- {vid}: DI LUAR kapal")


def print_ship_matrix(state: State, title: str) -> None:
    ship = state.problem.ship
    matrix = [["." for _ in range(ship.l)] for _ in range(ship.w)]

    for vid, p in state.placements.items():
        if not p.placed:
            continue
        v = state.problem.vehicles[vid]
        dx, dy = state.problem.dims(v, p.orientation)
        for x in range(p.x, p.x + dx):
            for y in range(p.y, p.y + dy):
                if 0 <= x < ship.w and 0 <= y < ship.l:
                    matrix[x][y] = vid

    print(f"\n=== {title} ===")
    print("Baris = x, kolom = y")
    print("    " + " ".join(f"{i:>3}" for i in range(ship.l)))
    for i, row in enumerate(matrix):
        print(f"{i:>2}: " + " ".join(f"{c:>3}" for c in row))


def is_feasible(state: State) -> bool:
    """Cek ulang dari nol (bukan delta): ga numpuk, ga keluar geladak, ga overcapacity."""
    problem = state.problem
    ship = problem.ship
    used: set[tuple[int, int]] = set()
    total_weight = 0
    for vid, p in state.placements.items():
        if not p.placed:
            continue
        v = problem.vehicles[vid]
        dx, dy = problem.dims(v, p.orientation)
        if p.x < 0 or p.y < 0 or p.x + dx > ship.w or p.y + dy > ship.l:
            return False
        for c in problem.cells(v, p):
            if c in used:
                return False
            used.add(c)
        total_weight += v.weight
    return total_weight <= ship.max_capacity


def print_result(result: HillClimbingResult, show_matrix: bool, show_history: bool) -> None:
    final = result.final_state

    if show_matrix:
        print_ship_matrix(result.initial_state, "Matriks geladak: STATE AWAL")
    print_vehicle_positions(final, "Detail penempatan: STATE AKHIR")
    if show_matrix:
        print_ship_matrix(final, "Matriks geladak: STATE AKHIR")

    print("\n=== Ringkasan ===")
    print(f"Algoritma           : {result.algorithm}")
    print(f"Seed                : {result.seed}")
    print(f"Value awal -> akhir : {result.initial_value} -> {result.final_value}")
    print(f"Iterasi             : {result.iterations}")
    print(f"Sideways moves      : {result.sideways_moves}")
    print(f"Neighbors evaluated : {result.neighbors_evaluated}")
    print(f"Durasi              : {result.duration:.4f} detik")
    print(f"Stop reason         : {result.stop_reason}")
    print(f"Di dalam kapal      : {final.inside_ids()}")
    print(f"Di luar kapal       : {final.outside_ids()}")
    print(f"State akhir valid   : {is_feasible(final)}")
    if show_history:
        print(f"History             : {result.history}")


def main() -> None:
    print("=== Program Main Hill Climbing ===")
    print("Pilih mode output:")
    print("1. DEBUG   -> semua detail + matriks awal & akhir + history")
    print("2. SUMMARY -> ringkasan + matriks awal & akhir")
    print("3. QUICK   -> ringkasan saja")
    mode_choice = ask_choice("Pilih mode [1/2/3]: ", ["1", "2", "3"])
    show_matrix = mode_choice in {"1", "2"}
    show_history = mode_choice == "1"

    print("\nPilih algoritma:")
    print("1. Steepest Ascent")
    print("2. Sideways Move")
    algorithm = "steepest" if ask_choice("Pilih algoritma [1/2]: ", ["1", "2"]) == "1" else "sideways"

    n_vehicles = ask_int("Jumlah kendaraan: ", 1)
    ship_w = ask_int("Lebar kapal: ", 1)
    ship_l = ask_int("Panjang kapal: ", 1)
    max_capacity = ask_int("Max capacity kapal (berat maksimum): ", 1)
    seed = ask_int("Seed: ", 0)
    max_iters = ask_int("Max iterasi: ", 1)
    max_sideways = ask_int("Max sideways: ", 0) if algorithm == "sideways" else 0

    print("\nPilih cara membuat kendaraan:")
    print("R. RANDOM -> ukuran, fee, berat dibuat acak berdasarkan seed")
    print("M. MANUAL -> input satu per satu")
    vehicle_mode = ask_choice("Pilih [R/M]: ", ["R", "M"])

    if vehicle_mode == "R":
        problem = generate_problem(n_vehicles=n_vehicles, ship_w=ship_w, ship_l=ship_l,
                                   max_capacity=max_capacity, seed=seed)
    else:
        problem = Problem(Ship(ship_w, ship_l, max_capacity), build_manual_vehicles(n_vehicles))

    total_weight = sum(v.weight for v in problem.vehicles.values())
    print(f"\nProblem dibuat: {len(problem.ids)} kendaraan, kapal {ship_w}x{ship_l}, capacity={problem.ship.max_capacity}")
    print(f"Total berat semua kendaraan: {total_weight}")
    print_vehicle_list(problem)

    initial_state = random_state(problem, seed)
    print("\nState awal dibuat secara random.")

    if algorithm == "steepest":
        result = steepest_ascent(problem, initial_state, seed=seed, max_iters=max_iters)
    else:
        result = sideways_move(problem, initial_state, seed=seed,
                               max_sideways=max_sideways, max_iters=max_iters)

    print_result(result, show_matrix, show_history)


if __name__ == "__main__":
    main()