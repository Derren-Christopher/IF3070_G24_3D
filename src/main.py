from __future__ import annotations

import random
import textwrap
from argparse import Namespace
from pathlib import Path

import ui
from define import HORIZONTAL, VERTICAL, Placement, Problem, Ship, State, Vehicle, generate_problem
from genetic_algorithm import genetic_algorithm
from hill_climbing import sideways_move, steepest_ascent
from simulated_annealing import simulated_annealing

try:
    import experiment as exp
    import visualizer as viz
    VIZ_OK, VIZ_ERR = True, ""
except ImportError as err:
    VIZ_OK, VIZ_ERR = False, str(err)

ALGOS = {"1": "Steepest Ascent", "2": "Sideways Move", "3": "Simulated Annealing", "4": "Genetic Algorithm"}
ALGO_DESC = {
    "1": "naik terus ke tetangga terbaik",
    "2": "boleh jalan di plateau (sideways)",
    "3": "terima solusi buruk, suhu turun",
    "4": "populasi, crossover & mutasi",
}


# ============================ BANNER ============================
def print_banner() -> None:
    art = [
        " ██████╗ █████╗ ██████╗  ██████╗  ██████╗ ",
        "██╔════╝██╔══██╗██╔══██╗██╔════╝ ██╔═══██╗",
        "██║     ███████║██████╔╝██║  ███╗██║   ██║",
        "██║     ██╔══██║██╔══██╗██║   ██║██║   ██║",
        "╚██████╗██║  ██║██║  ██║╚██████╔╝╚██████╔╝",
        " ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ",
    ]
    ui.banner(
        art,
        "P L A C E M E N T   O P T I M I Z E R",
        ["By 3D", "Tugas Besar IF3070 - 2026"],
        "Steepest Ascent  •  Sideways  •  Simulated Annealing  •  GA",
    )


# ============================ INPUT ============================
def ask_int(prompt: str, minimum: int = 0) -> int:
    while True:
        try:
            value = int(input(ui.prompt(prompt)))
            if value >= minimum:
                return value
            ui.warn(f"Nilai harus >= {minimum}.")
        except ValueError:
            ui.warn("Input harus angka bulat.")


def ask_int_default(prompt: str, default: int, minimum: int = 0) -> int:
    while True:
        raw = input(ui.prompt(f"{prompt} {ui.dim(f'[default {default}]')}: ")).strip()
        if raw == "":
            return default
        try:
            value = int(raw)
            if value >= minimum:
                return value
            ui.warn(f"Nilai harus >= {minimum}.")
        except ValueError:
            ui.warn("Input harus angka bulat.")


def ask_float(prompt: str, default: float) -> float:
    while True:
        raw = input(ui.prompt(f"{prompt} {ui.dim(f'[default {default}]')}: ")).strip()
        if raw == "":
            return default
        try:
            return float(raw)
        except ValueError:
            ui.warn("Input harus angka.")


def ask_rate(prompt: str, default: float) -> float:
    while True:
        value = ask_float(prompt, default)
        if 0 <= value <= 1:
            return value
        ui.warn("Nilai harus di antara 0 dan 1.")


def ask_choice(prompt: str, options: list[str]) -> str:
    while True:
        value = input(ui.prompt(prompt)).strip().upper()
        if value in [opt.upper() for opt in options]:
            return value
        ui.warn(f"Pilih salah satu: {', '.join(options)}")


def ask_yes_no(prompt: str) -> bool:
    while True:
        value = input(ui.prompt(prompt)).strip().lower()
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        ui.warn("Jawab y/yes atau n/no.")


def build_manual_vehicles(n_vehicles: int) -> list[Vehicle]:
    vehicles: list[Vehicle] = []
    ui.section("Input kendaraan manual")
    for i in range(1, n_vehicles + 1):
        print(f"\n  {ui.vtag(f'V{i:02d}')} {ui.dim(f'(kendaraan {i} dari {n_vehicles})')}")
        w = ask_int(f"Lebar kendaraan {i}: ", 1)
        l = ask_int(f"Panjang kendaraan {i}: ", 1)
        fee = ask_int(f"Fee kendaraan {i}: ", 0)
        weight = ask_int(f"Berat kendaraan {i}: ", 0)
        eta = ask_int(f"ETA kendaraan {i}: ", 0)
        vehicles.append(Vehicle(f"V{i:02d}", w, l, fee, weight, eta))
    return vehicles


def user_placement(problem: Problem) -> State:
    while True:
        placements: dict[str, Placement] = {}
        ui.section("Placement awal manual")
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
        ui.error("Placement tidak valid (numpuk / keluar kapal / overweight). Coba lagi.")


def setup_problem(min_vehicles: int) -> tuple[Problem, int]:
    ui.section("Setup problem")
    n_vehicles = ask_int(f"Jumlah kendaraan (min {min_vehicles}): ", min_vehicles)
    ship_w = ask_int("Lebar kapal: ", 1)
    ship_l = ask_int("Panjang kapal: ", 1)
    max_capacity = ask_int("Max capacity kapal (berat maksimum): ", 1)
    seed = ask_int("Seed: ", 0)

    print("\n  Pilih cara membuat kendaraan:")
    ui.menu([
        ("R", "RANDOM", "ukuran, fee, berat dibuat acak berdasarkan seed"),
        ("M", "MANUAL", "input satu per satu"),
    ])
    if ask_choice("Pilih [R/M]: ", ["R", "M"]) == "R":
        problem = generate_problem(n_vehicles=n_vehicles, ship_w=ship_w, ship_l=ship_l,
                                   max_capacity=max_capacity, seed=seed)
    else:
        problem = Problem(Ship(ship_w, ship_l, max_capacity), build_manual_vehicles(n_vehicles))

    total_weight = sum(v.weight for v in problem.vehicles.values())
    ui.success(f"Problem dibuat: {ui.bold(len(problem.ids))} kendaraan, kapal "
               f"{ui.bold(f'{ship_w}x{ship_l}')}, capacity {ui.bold(problem.ship.max_capacity)}")
    ui.info(f"Total berat semua kendaraan: {ui.bold(total_weight)}")
    print_vehicle_list(problem)
    return problem, seed


def initial_state_for(problem: Problem, seed: int) -> State:
    print("\n  State awal:")
    ui.menu([
        ("R", "RANDOM", "dari seed"),
        ("M", "MANUAL", "input posisi tiap kendaraan"),
    ])
    if ask_choice("Pilih [R/M]: ", ["R", "M"]) == "M":
        return user_placement(problem)
    ui.success("State awal dibuat secara random.")
    return problem.random_state(random.Random(seed), attempts=40)


# ============================ OUTPUT ============================
def print_vehicle_list(problem: Problem) -> None:
    ui.section("Daftar kendaraan")
    rows = [[ui.vtag(v.id), f"{v.w}x{v.l}", v.fee, v.weight, v.eta] for v in problem.vehicles.values()]
    ui.table(["ID", "Ukuran", "Fee", "Berat", "ETA"], rows, ["l", "l", "r", "r", "r"])


def print_vehicle_positions(state: State, title: str) -> None:
    ui.section(title)
    cap = state.problem.ship.max_capacity
    print(f"  {ui.dim('Value (total fee)'.ljust(18))} {ui.good(state.value)}")
    print(f"  {ui.dim('Beban kapal'.ljust(18))} {ui.bar(state.weight / cap)}  {ui.dim(f'{state.weight} / {cap}')}\n")
    rows = []
    for vid, p in state.placements.items():
        if p.placed:
            rows.append([ui.vtag(vid), ui.good("DI DALAM"), p.x, p.y, p.orientation])
        else:
            rows.append([ui.vtag(vid), ui.dim("di luar"), ui.dim("-"), ui.dim("-"), ui.dim(p.orientation)])
    ui.table(["ID", "Status", "x", "y", "Orientasi"], rows, ["l", "l", "r", "r", "l"])


def print_ship_matrix(state: State, title: str) -> None:
    ship = state.problem.ship
    cells: list[list] = [[None] * ship.l for _ in range(ship.w)]
    for vid, p in state.placements.items():
        if not p.placed:
            continue
        v = state.problem.vehicles[vid]
        dx, dy = state.problem.dims(v, p.orientation)
        for x in range(p.x, p.x + dx):
            for y in range(p.y, p.y + dy):
                if 0 <= x < ship.w and 0 <= y < ship.l:
                    cells[x][y] = (vid, x == p.x and y == p.y)
    ui.section(title)
    print(ui.dim("  Baris = x, kolom = y\n"))
    ui.grid(cells)


def is_feasible(state: State) -> bool:
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
        print_ship_matrix(result.initial_state, "Matriks geladak · STATE AWAL")
    print_vehicle_positions(final, "Detail penempatan · STATE AKHIR (terbaik)")
    if show_matrix:
        print_ship_matrix(final, "Matriks geladak · STATE AKHIR (terbaik)")

    delta = result.final_value - result.initial_value
    pairs: list[tuple[str, str]] = [
        ("Algoritma", ui.accent(result.algorithm)),
        ("Seed", str(result.seed)),
        ("Value awal → akhir", f"{result.initial_value} → {ui.good(result.final_value)}  {ui.good(f'({delta:+g})')}"),
    ]

    if hasattr(result, "exp_log"):
        pairs += [
            ("Value state terakhir", str(result.last_state.value)),
            ("Iterasi", str(result.iterations)),
            ("Neighbors evaluated", str(result.neighbors_evaluated)),
            ("Move diterima", str(result.accepted)),
            ("Move lebih buruk diterima", str(result.worse_accepted)),
            ("Suhu awal / akhir", f"{result.init_temp} / {result.stopping_temp}"),
            ("Cooling rate", str(result.cooling_rate)),
            ("Stuck count", f"{result.stuck_count} (window {result.stuck_window} iterasi)"),
            ("Stuck di iterasi", f"{result.stuck_iters[:10]}{' ...' if len(result.stuck_iters) > 10 else ''}"),
            ("Final = local optimum", ui.good("ya") if result.final_is_local_optimum else ui.gold("tidak")),
            ("Stop reason", str(result.stop_reason)),
        ]
    elif hasattr(result, "sideways_moves"):
        pairs += [
            ("Iterasi", str(result.iterations)),
            ("Sideways moves", str(result.sideways_moves)),
            ("Neighbors evaluated", str(result.neighbors_evaluated)),
            ("Stop reason", str(result.stop_reason)),
        ]
    else:
        pairs += [
            ("Ukuran populasi", str(result.population_size)),
            ("Generasi", str(result.generations)),
            ("Rata-rata populasi", f"{result.history_avg[0]:.3f} → {result.history_avg[-1]:.3f}"),
            ("Parameter", ""),
        ]
        pairs += [(f"  · {k}", str(v)) for k, v in result.params.items()]

    pairs += [
        ("Durasi", f"{result.duration:.4f} detik"),
        ("Di dalam kapal", ", ".join(final.inside_ids()) or "-"),
        ("Di luar kapal", ", ".join(final.outside_ids()) or "-"),
    ]
    ui.section("Ringkasan")
    ui.box("Hasil", ui.kv_lines(pairs))

    ui.section("Validasi otomatis")
    checks = verify_result(result)
    for name, ok in checks:
        ui.ok_line(name, ok)
    passed = sum(ok for _, ok in checks)
    summary = f"{passed}/{len(checks)} pengecekan lolos"
    print("\n  " + (ui.good(summary) if passed == len(checks) else ui.bad(summary)))

    if show_history:
        print_history(result)


def print_history(result) -> None:
    ui.section("History")
    if hasattr(result, "exp_log"):
        ui.trend("current", result.history)
        ui.trend("best", result.best_history)
        ui.trend("suhu", result.temp_history, "{:.3g}")
        print(f"\n  {ui.dim('Contoh log e^(delta/T)')}")
        rows = [[it, delta, f"{prob:.4f}"] for it, delta, prob in result.exp_log[:10]]
        ui.table(["Iterasi", "Delta", "Probabilitas"], rows, ["r", "r", "r"])
    elif hasattr(result, "sideways_moves"):
        ui.trend("value", result.history)
        print(f"\n  {ui.dim('Sampel:')} {sample_list(result.history)}")
    else:
        ui.trend("best", result.history_best)
        ui.trend("avg", result.history_avg, "{:.2f}")
        print(f"\n  {ui.dim('Best (disampel):')} {sample_list(result.history_best)}")


# ============================ PARAMETER ============================
def ask_hc_params(algo: str) -> dict:
    ui.section("Parameter Hill Climbing  " + ui.dim("(Enter = default)"))
    params = {"max_iters": ask_int_default("Max iterasi", 10000, 1)}
    if algo == "2":
        params["max_sideways"] = ask_int_default("Max sideways", 100, 0)
    return params


def ask_sa_params() -> dict:
    ui.section("Parameter Simulated Annealing  " + ui.dim("(Enter = default)"))
    while True:
        init_temp = ask_float("Suhu awal", 50.0)
        cooling_rate = ask_float("Cooling rate (0 < r < 1)", 0.999)
        stopping_temp = ask_float("Suhu berhenti (> 0)", 0.01)
        if not (0 < cooling_rate < 1):
            ui.warn("Cooling rate harus di antara 0 dan 1.")
        elif stopping_temp <= 0 or init_temp <= stopping_temp:
            ui.warn("Suhu berhenti harus > 0 dan lebih kecil dari suhu awal.")
        else:
            break
    stuck_window = ask_int_default("Stuck window (iterasi tanpa perubahan)", 50, 1)
    return dict(init_temp=init_temp, cooling_rate=cooling_rate, stopping_temp=stopping_temp, stuck_window=stuck_window)


def ask_ga_params() -> dict:
    ui.section("Parameter Genetic Algorithm  " + ui.dim("(Enter = default)"))
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


# ============================ RUN ============================
def run_single(algo: str, show_matrix: bool, show_history: bool) -> None:
    problem, seed = setup_problem(2 if algo == "4" else 1)
    if algo == "4":
        ui.info("Populasi awal dibuat secara random di dalam algoritma.")
        params, initial = ask_ga_params(), None
    else:
        initial = initial_state_for(problem, seed)
        params = ask_sa_params() if algo == "3" else ask_hc_params(algo)

    want_viz = want_gif = False
    print()
    if VIZ_OK:
        want_viz = ask_yes_no("Simpan visualisasi (PNG) setelah selesai? (y/n): ")
        want_gif = want_viz and ask_yes_no("Buat animasi GIF juga? (y/n): ")
    elif ask_yes_no("Mau visualisasi? (y/n): "):
        ui.warn(f"Visualisasi dimatikan ({VIZ_ERR}). Coba: pip install matplotlib")

    trace: list | None = [] if want_viz else None
    print()
    with ui.Spinner(f"Menjalankan {ALGOS[algo]}"):
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
        with ui.Spinner("Menyimpan visualisasi"):
            save_visuals(result, trace, want_gif)


def save_visuals(result, trace: list, want_gif: bool) -> None:
    out = Path("output")
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
    ui.info(f"Visualisasi disimpan di folder: {ui.bold(out.resolve())}")


def compare_all() -> None:
    if not VIZ_OK:
        ui.error(f"Mode bandingkan butuh experiment.py, visualizer.py, dan matplotlib ({VIZ_ERR}).")
        return
    problem, seed = setup_problem(2)
    ui.section("Pengaturan perbandingan")
    runs_n = ask_int_default("Jumlah seed per algoritma", 10, 1)
    out = Path(input(ui.prompt(f"Folder output {ui.dim('[default hasil]')}: ")).strip() or "hasil")
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
    print(f"\n  Suite tambahan {ui.dim('(pisah koma)')}: {ui.accent('ga, sideways, scale, capacity, trace')}")
    print(ui.dim("  (scale & capacity bikin problem random baru dari ukuran kapal di atas)"))
    extra = [s.strip() for s in (input(ui.prompt(f"Suite tambahan {ui.dim('[Enter = trace]')}: ")).strip() or "trace").split(",") if s.strip()]
    bad = [s for s in extra if s not in exp.ALL_SUITES or s == "main"]
    if bad:
        ui.warn(f"Suite diabaikan: {bad}")
        extra = [s for s in extra if s not in bad]

    ub = viz.upper_bound(problem)
    seeds, sseeds = list(range(runs_n)), list(range(min(runs_n, 5)))
    ui.info(f"Batas atas value (relaksasi): {ui.bold(f'{ub:.1f}')}")
    ui.section("Suite: main")
    exp.suite_main(problem, args, out, ub, seeds)
    for s in extra:
        ui.section(f"Suite: {s}")
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
    ui.success(f"Selesai. Hasil (CSV, tabel, statistik, grafik) disimpan di: {ui.bold(out.resolve())}")


# ============================ MAIN ============================
def goodbye() -> None:
    print()
    ui.box("Sampai jumpa", [
        ui.center("Terima kasih sudah memakai Cargo Placement Optimizer!", ui.WIDTH - 4),
        ui.center(ui.dim("Semoga value-nya selalu maksimal, AMINNNN."), ui.WIDTH - 4),
    ], color=ui.PINK)
    print()


def main() -> None:
    print_banner()
    print("  Halo, selamat datang di " + ui.accent("Cargo Placement Optimizer") + " by 3D!")
    print(ui.dim("  Yuk pilih dulu mode outputnya."))
    try:
        while True:
            ui.section("Pilih mode output")
            ui.menu([
                ("1", "DEBUG", "semua detailnya + matriks awal & akhir + history algoritma (buat debugging)"),
                ("2", "SUMMARY", "ringkasan algoritma + matriks awal & akhir (visualisasi + cek data besar)"),
                ("3", "QUICK", "ringkasannya saja (buat tes data besar)"),
            ])
            mode_choice = ask_choice("Pilih mode [1/2/3]: ", ["1", "2", "3"])
            show_matrix = mode_choice in {"1", "2"}
            show_history = mode_choice == "1"

            ui.section("Pilih algoritma")
            ui.menu([(k, name, ALGO_DESC[k]) for k, name in ALGOS.items()]
                    + [("5", "BANDINGKAN SEMUA", "banyak seed + grafik + statistik")])
            choice = ask_choice("Pilih algoritma [1/2/3/4/5]: ", ["1", "2", "3", "4", "5"])

            if choice == "5":
                compare_all()
            else:
                run_single(choice, show_matrix, show_history)

            print()
            if not ask_yes_no("Jalankan lagi? (y/n): "):
                break
    except (KeyboardInterrupt, EOFError):
        print()
        ui.warn("Dihentikan oleh pengguna.")
    goodbye()


if __name__ == "__main__":
    main()