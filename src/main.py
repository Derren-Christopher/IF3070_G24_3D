"""Main gabungan: satu interface buat semua algoritma local search penempatan kendaraan di kapal kargo.

    1. Hill Climbing - Steepest Ascent
    2. Hill Climbing - Sideways Move
    3. Simulated Annealing
    4. Genetic Algorithm
    5. BANDINGKAN SEMUA (banyak seed + grafik + statistik, pakai experiment.py & visualizer.py)

Jalankan:  python main.py
File yang dibutuhkan (satu folder): define.py, hill_climbing.py, simulated_annealing.py,
genetic_algorithm.py, dan (buat grafik) visualizer.py + experiment.py + matplotlib.
"""
from __future__ import annotations

import random
from argparse import Namespace
from pathlib import Path

from define import HORIZONTAL, VERTICAL, Placement, Problem, Ship, State, Vehicle, generate_problem
from genetic_algorithm import genetic_algorithm
from hill_climbing import sideways_move, steepest_ascent
from simulated_annealing import simulated_annealing

try:  # visualisasi opsional: butuh matplotlib
    import experiment as exp
    import visualizer as viz
    VIZ_OK, VIZ_ERR = True, ""
except ImportError as err:
    VIZ_OK, VIZ_ERR = False, str(err)

ALGOS = {"1": "Steepest Ascent", "2": "Sideways Move", "3": "Simulated Annealing", "4": "Genetic Algorithm"}


# ====================================================================== input helper

def ask_int(prompt: str, minimum: int = 0) -> int:
    while True:
        try:
            value = int(input(prompt))
            if value >= minimum:
                return value
            print(f"Nilai harus >= {minimum}.")
        except ValueError:
            print("Input harus angka bulat.")


def ask_int_default(prompt: str, default: int, minimum: int = 0) -> int:
    while True:
        raw = input(f"{prompt} [default {default}]: ").strip()
        if raw == "":
            return default
        try:
            value = int(raw)
            if value >= minimum:
                return value
            print(f"Nilai harus >= {minimum}.")
        except ValueError:
            print("Input harus angka bulat.")


def ask_float(prompt: str, default: float) -> float:
    while True:
        raw = input(f"{prompt} [default {default}]: ").strip()
        if raw == "":
            return default
        try:
            return float(raw)
        except ValueError:
            print("Input harus angka.")


def ask_rate(prompt: str, default: float) -> float:
    while True:
        value = ask_float(prompt, default)
        if 0 <= value <= 1:
            return value
        print("Nilai harus di antara 0 dan 1.")


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


# ====================================================================== bikin problem & state awal

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


def user_placement(problem: Problem) -> State:
    """State awal manual. Diulang kalau hasilnya ga valid (numpuk/keluar geladak/overcapacity)."""
    while True:
        placements: dict[str, Placement] = {}
        print("\nMasukkan placement awal tiap kendaraan.")
        for vid in problem.ids:
            if ask_yes_no(f"{vid} masuk kapal? (y/n): "):
                o = ask_choice(f"Orientasi {vid} ({HORIZONTAL}/{VERTICAL})? ", [HORIZONTAL, VERTICAL])
                x = ask_int(f"x {vid}: ", 0)
                y = ask_int(f"y {vid}: ", 0)
                placements[vid] = Placement(x, y, o.capitalize())
            else:
                o = ask_choice(f"Orientasi default {vid} saat di luar kapal ({HORIZONTAL}/{VERTICAL})? ",
                               [HORIZONTAL, VERTICAL])
                placements[vid] = Placement(None, None, o.capitalize())
        state = State(problem, placements)
        if is_feasible(state):
            return state
        print("\n[!] State awal ga valid (numpuk / keluar geladak / overcapacity). Masukkan ulang.")


def setup_problem(min_vehicles: int) -> tuple[Problem, int]:
    n_vehicles = ask_int(f"Jumlah kendaraan (min {min_vehicles}): ", min_vehicles)
    ship_w = ask_int("Lebar kapal: ", 1)
    ship_l = ask_int("Panjang kapal: ", 1)
    max_capacity = ask_int("Max capacity kapal (berat maksimum): ", 1)
    seed = ask_int("Seed: ", 0)

    print("\nPilih cara membuat kendaraan:")
    print("R. RANDOM -> ukuran, fee, berat dibuat acak berdasarkan seed")
    print("M. MANUAL -> input satu per satu")
    if ask_choice("Pilih [R/M]: ", ["R", "M"]) == "R":
        problem = generate_problem(n_vehicles=n_vehicles, ship_w=ship_w, ship_l=ship_l,
                                   max_capacity=max_capacity, seed=seed)
    else:
        problem = Problem(Ship(ship_w, ship_l, max_capacity), build_manual_vehicles(n_vehicles))

    total_weight = sum(v.weight for v in problem.vehicles.values())
    print(f"\nProblem dibuat: {len(problem.ids)} kendaraan, kapal {ship_w}x{ship_l}, capacity={problem.ship.max_capacity}")
    print(f"Total berat semua kendaraan: {total_weight}")
    print_vehicle_list(problem)
    return problem, seed


def initial_state_for(problem: Problem, seed: int) -> State:
    print("\nState awal:  R. RANDOM (dari seed)   M. MANUAL (input posisi tiap kendaraan)")
    if ask_choice("Pilih [R/M]: ", ["R", "M"]) == "M":
        return user_placement(problem)
    print("State awal dibuat secara random.")
    return problem.random_state(random.Random(seed), attempts=40)


# ====================================================================== cetak

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
    problem, ship = state.problem, state.problem.ship
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


def sample_list(data: list, n: int = 20) -> list:
    """Ambil n titik merata dari list panjang biar output debug ga kebanyakan."""
    if len(data) <= n:
        return data
    step = len(data) / n
    return [data[int(i * step)] for i in range(n)] + [data[-1]]


def best_curve(result) -> list:
    for attr in ("best_history", "history", "history_best"):
        h = getattr(result, attr, None)
        if h is not None:
            return list(h)
    return []


def verify_result(result) -> list[tuple[str, bool]]:
    """Invarian yang harus selalu benar, dihitung independen dari kode algoritma."""
    final = result.final_state
    problem = final.problem
    inside = final.inside_ids()
    curve = best_curve(result)
    return [
        ("State akhir valid (tidak numpuk/keluar/overweight)", is_feasible(final)),
        ("Value == jumlah fee kendaraan di dalam", final.value == sum(problem.vehicles[i].fee for i in inside)),
        ("Berat == jumlah berat kendaraan di dalam", final.weight == sum(problem.vehicles[i].weight for i in inside)),
        ("Kurva terbaik tidak pernah turun", all(a <= b for a, b in zip(curve, curve[1:]))),
        ("Value akhir == ujung kurva terbaik", bool(curve) and curve[-1] == result.final_value),
        ("Value akhir >= value awal", result.final_value >= result.initial_value),
    ]


def print_result(result, show_matrix: bool, show_history: bool) -> None:
    final = result.final_state
    if show_matrix:
        print_ship_matrix(result.initial_state, "Matriks geladak: STATE AWAL")
    print_vehicle_positions(final, "Detail penempatan: STATE AKHIR (terbaik)")
    if show_matrix:
        print_ship_matrix(final, "Matriks geladak: STATE AKHIR (terbaik)")

    print("\n=== Ringkasan ===")
    print(f"Algoritma             : {result.algorithm}")
    print(f"Seed                  : {result.seed}")
    print(f"Value awal -> akhir   : {result.initial_value} -> {result.final_value}")

    if hasattr(result, "exp_log"):  # Simulated Annealing
        print(f"Value state terakhir  : {result.last_state.value}")
        print(f"Iterasi               : {result.iterations}")
        print(f"Neighbors evaluated   : {result.neighbors_evaluated}")
        print(f"Move diterima         : {result.accepted}")
        print(f"Move lebih buruk diterima : {result.worse_accepted}")
        print(f"Suhu awal / akhir     : {result.init_temp} / {result.stopping_temp}")
        print(f"Cooling rate          : {result.cooling_rate}")
        print(f"Stuck count           : {result.stuck_count} (window {result.stuck_window} iterasi)")
        print(f"Stuck di iterasi      : {result.stuck_iters[:10]}{' ...' if len(result.stuck_iters) > 10 else ''}")
        print(f"Final = local optimum : {result.final_is_local_optimum}")
        print(f"Stop reason           : {result.stop_reason}")
    elif hasattr(result, "sideways_moves"):  # Hill Climbing
        print(f"Iterasi               : {result.iterations}")
        print(f"Sideways moves        : {result.sideways_moves}")
        print(f"Neighbors evaluated   : {result.neighbors_evaluated}")
        print(f"Stop reason           : {result.stop_reason}")
    else:  # Genetic Algorithm
        print(f"Ukuran populasi       : {result.population_size}")
        print(f"Generasi              : {result.generations}")
        print(f"Rata-rata populasi    : {result.history_avg[0]:.3f} -> {result.history_avg[-1]:.3f}")
        print("Parameter             :")
        for key, val in result.params.items():
            print(f"  - {key}: {val}")
    print(f"Durasi                : {result.duration:.4f} detik")
    print(f"Di dalam kapal        : {final.inside_ids()}")
    print(f"Di luar kapal         : {final.outside_ids()}")

    print("\n=== Validasi otomatis ===")
    for name, ok in verify_result(result):
        print(f"[{'OK' if ok else 'GAGAL'}] {name}")

    if show_history:
        if hasattr(result, "exp_log"):
            print(f"\nHistory (current, disampel) : {sample_list(result.history)}")
            print(f"History (best, disampel)    : {sample_list(result.best_history)}")
            print(f"Suhu (disampel)             : {[round(t, 3) for t in sample_list(result.temp_history)]}")
            print("Contoh log e^(delta/T) [iterasi, delta, probabilitas]:")
            for it, delta, prob in result.exp_log[:10]:
                print(f"  iter {it:>5} | delta {delta:>5} | prob {prob:.4f}")
        elif hasattr(result, "sideways_moves"):
            print(f"\nHistory : {result.history}")
        else:
            print(f"\nHistory best (disampel) : {sample_list(result.history_best)}")
            print(f"History avg (disampel)  : {[round(a, 2) for a in sample_list(result.history_avg)]}")


# ====================================================================== parameter per algoritma

def ask_hc_params(algo: str) -> dict:
    print("\nParameter Hill Climbing (Enter untuk default):")
    params = {"max_iters": ask_int_default("Max iterasi", 10000, 1)}
    if algo == "2":
        params["max_sideways"] = ask_int_default("Max sideways", 100, 0)
    return params


def ask_sa_params() -> dict:
    print("\nParameter Simulated Annealing (Enter untuk default):")
    while True:
        init_temp = ask_float("Suhu awal", 50.0)
        cooling_rate = ask_float("Cooling rate (0 < r < 1)", 0.999)
        stopping_temp = ask_float("Suhu berhenti (> 0)", 0.01)
        if not (0 < cooling_rate < 1):
            print("Cooling rate harus di antara 0 dan 1.")
        elif stopping_temp <= 0 or init_temp <= stopping_temp:
            print("Suhu berhenti harus > 0 dan lebih kecil dari suhu awal.")
        else:
            break
    stuck_window = ask_int_default("Stuck window (iterasi tanpa perubahan)", 50, 1)
    return dict(init_temp=init_temp, cooling_rate=cooling_rate, stopping_temp=stopping_temp, stuck_window=stuck_window)


def ask_ga_params() -> dict:
    print("\nParameter Genetic Algorithm (Enter untuk default):")
    population_size = ask_int_default("Ukuran populasi", 50, 2)
    return dict(
        population_size=population_size,
        generations=ask_int_default("Jumlah generasi", 300, 1),
        crossover_rate=ask_rate("Crossover rate (0-1)", 0.9),
        mutation_rate=ask_rate("Mutation rate (0-1)", 0.9),
        mutation_steps=ask_int_default("Maks mutasi per anak", 6, 1),
        elite_size=min(ask_int_default("Elite size", 2, 0), population_size),
        tournament_k=ask_int_default("Ukuran turnamen", 2, 1),
        init_attempts=ask_int_default("Percobaan menaruh kendaraan saat bikin state awal", 40, 1),
    )


# ====================================================================== jalanin satu algoritma

def run_single(algo: str, show_matrix: bool, show_history: bool) -> None:
    problem, seed = setup_problem(2 if algo == "4" else 1)
    if algo == "4":
        print("\nPopulasi awal dibuat secara random di dalam algoritma.")
        params, initial = ask_ga_params(), None
    else:
        initial = initial_state_for(problem, seed)
        params = ask_sa_params() if algo == "3" else ask_hc_params(algo)

    want_viz = want_gif = False
    if VIZ_OK:
        want_viz = ask_yes_no("\nSimpan visualisasi (PNG) setelah selesai? (y/n): ")
        want_gif = want_viz and ask_yes_no("Buat animasi GIF juga? (y/n): ")
    elif ask_yes_no("\nMau visualisasi? (y/n): "):
        print(f"[!] Visualisasi dimatikan ({VIZ_ERR}). Coba: pip install matplotlib")

    trace: list | None = [] if want_viz else None
    if algo == "1":
        result = steepest_ascent(problem, initial, seed=seed, max_iters=params["max_iters"], trace=trace)
    elif algo == "2":
        result = sideways_move(problem, initial, seed=seed, max_sideways=params["max_sideways"],
                               max_iters=params["max_iters"], trace=trace)
    elif algo == "3":
        result = simulated_annealing(problem, initial, seed=seed, trace=trace, **params)
    else:
        result = genetic_algorithm(problem, seed=seed, trace=trace, **params)

    print_result(result, show_matrix, show_history)
    if want_viz:
        save_visuals(result, trace, want_gif)


def save_visuals(result, trace: list, want_gif: bool) -> None:
    out = Path("hasil_run")
    out.mkdir(exist_ok=True)
    tag = f"{exp.safe(result.algorithm)}_seed{result.seed}"
    title = f"{result.algorithm} (seed {result.seed})"
    viz.plot_state_detail(result.final_state, out / f"state_{tag}.png", f"{title} - state akhir")
    viz.plot_run(result, out / f"run_{tag}.png", title)
    if hasattr(result, "exp_log"):
        viz.plot_sa_stats({result.algorithm: [result]}, out / f"sa_{tag}.png")
    if trace:
        viz.plot_snapshots(trace, out / f"snapshots_{tag}.png", title)
        if want_gif:
            viz.animate_trace(trace, out / f"anim_{tag}.gif", title)
    print(f"\nVisualisasi disimpan di folder: {out.resolve()}")


# ====================================================================== bandingkan semua

def compare_all() -> None:
    if not VIZ_OK:
        print(f"[!] Mode bandingkan butuh experiment.py, visualizer.py, dan matplotlib ({VIZ_ERR}).")
        return
    problem, seed = setup_problem(2)
    runs_n = ask_int_default("\nJumlah seed per algoritma", 10, 1)
    out = Path(input("Folder output [default hasil]: ").strip() or "hasil")
    out.mkdir(parents=True, exist_ok=True)
    args = Namespace(
        n_vehicles=len(problem.ids), ship_w=problem.ship.w, ship_l=problem.ship.l, problem_seed=seed,
        max_iters=10000, max_sideways=100, population=50, generations=300,
        sa_temp=50.0, sa_cooling=0.999, sa_stop=0.01, scale_n=[10, 15, 20, 25, 30, 40])
    if not ask_yes_no("Pakai parameter default semua algoritma? (y/n): "):
        args.max_sideways = ask_int_default("Max sideways (Sideways Move)", 100, 0)
        args.sa_temp = ask_float("SA suhu awal", 50.0)
        args.sa_cooling = ask_rate("SA cooling rate", 0.999)
        args.population = ask_int_default("GA ukuran populasi", 50, 2)
        args.generations = ask_int_default("GA jumlah generasi", 300, 1)
    print("\nSuite tambahan (pisah koma): ga, sideways, scale, capacity, trace")
    print("  (scale & capacity bikin problem random baru dari ukuran kapal di atas)")
    extra = [s.strip() for s in (input("Suite tambahan [Enter = trace]: ").strip() or "trace").split(",") if s.strip()]
    bad = [s for s in extra if s not in exp.ALL_SUITES or s == "main"]
    if bad:
        print(f"Suite diabaikan: {bad}")
        extra = [s for s in extra if s not in bad]

    ub = viz.upper_bound(problem)
    seeds, sseeds = list(range(runs_n)), list(range(min(runs_n, 5)))
    print(f"\nBatas atas value (relaksasi): {ub:.1f}\n\n[suite: main]")
    exp.suite_main(problem, args, out, ub, seeds)
    for s in extra:
        print(f"\n[suite: {s}]")
        if s == "ga":
            exp.suite_ga(problem, args, out, sseeds)
        elif s == "sideways":
            exp.suite_sideways(problem, args, out, sseeds)
        elif s == "scale":
            exp.suite_series(args, out, sseeds, "n")
        elif s == "capacity":
            exp.suite_series(args, out, sseeds, "capacity")
        elif s == "trace":
            exp.suite_trace(problem, args, out)
    with open(out / "DAFTAR_GAMBAR.md", "w", encoding="utf-8") as f:
        f.write("# Daftar gambar & usulan caption\n\n")
        for i, (fn, cap) in enumerate(sorted(viz.CAPTIONS), start=1):
            f.write(f"{i}. `{fn}` - {cap}\n")
    print(f"\nSelesai. Hasil (CSV, tabel, statistik, grafik) disimpan di: {out.resolve()}")


# ====================================================================== main

def main() -> None:
    print("=== Program Main Local Search: Penempatan Kendaraan di Kapal Kargo ===")
    while True:
        print("\nPilih mode output:")
        print("1. DEBUG   -> semua detail + matriks awal & akhir + history")
        print("2. SUMMARY -> ringkasan + matriks awal & akhir")
        print("3. QUICK   -> ringkasan saja")
        mode_choice = ask_choice("Pilih mode [1/2/3]: ", ["1", "2", "3"])
        show_matrix = mode_choice in {"1", "2"}
        show_history = mode_choice == "1"

        print("\nPilih algoritma:")
        for k, name in ALGOS.items():
            print(f"{k}. {name}")
        print("5. BANDINGKAN SEMUA (banyak seed + grafik + statistik)")
        choice = ask_choice("Pilih algoritma [1/2/3/4/5]: ", ["1", "2", "3", "4", "5"])

        if choice == "5":
            compare_all()
        else:
            run_single(choice, show_matrix, show_history)

        if not ask_yes_no("\nJalankan lagi? (y/n): "):
            print("Selesai.")
            break


if __name__ == "__main__":
    main()