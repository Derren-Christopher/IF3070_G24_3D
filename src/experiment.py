"""Runner experiment lengkap: banyak seed, banyak suite analisis, CSV + grafik + statistik + daftar caption.

Contoh:
    python experiment.py                              # suite main + trace, 25 kendaraan, kapal 10x20, 10 seed
    python experiment.py --quick                      # versi cepat buat ngecek program jalan
    python experiment.py --suites all                 # semua analisis (lama!)
    python experiment.py --suites main,ga,sideways    # pilih suite tertentu
    python experiment.py --pdf                        # simpan juga PDF vektor tiap gambar

Suite:
    main      perbandingan algoritma (grafik 01-09, tabel, uji statistik, detail state)
    ga        sensitivitas parameter GA: populasi, generasi, crossover, mutation, elite, turnamen + heatmap
    sideways  pengaruh batas sideways move pada Hill Climbing
    scale     skalabilitas terhadap jumlah kendaraan
    capacity  pengaruh rasio kapasitas kapal
    trace     snapshot & animasi GIF perkembangan layout (seed 0)

Semua algoritma dijalankan di problem YANG SAMA dengan seed 0..runs-1.
Algoritma yang dibandingkan didaftarkan di build_algorithms(): Steepest Ascent, Sideways, SA, GA.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import random
import statistics
from pathlib import Path

from define import Problem, State, generate_problem
from genetic_algorithm import genetic_algorithm
from hill_climbing import sideways_move, steepest_ascent
import visualizer as viz

from simulated_annealing import simulated_annealing

ALL_SUITES = ["main", "ga", "sideways", "scale", "capacity", "trace"]


# ---------------------------------------------------------------- util

def is_feasible(state: State) -> bool:
    """Validator independen (hitung ulang dari nol)."""
    problem, ship = state.problem, state.problem.ship
    used, weight = set(), 0
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
        weight += v.weight
    return weight <= ship.max_capacity


def safe(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name).strip("_")


def build_algorithms(args) -> dict:
    """nama -> fungsi(problem, seed, trace=None) -> result. Semua mulai dari problem yang sama.
    Contoh nambah SA:
        "Simulated Annealing": lambda p, s, trace=None: simulated_annealing(p, init(p, s), seed=s, ...),
    (result SA harus punya: algorithm, seed, initial_state, final_state, initial_value, final_value,
     duration, history)."""
    def init(problem: Problem, seed: int) -> State:  # state awal HC (sama kayak main HC)
        return problem.random_state(random.Random(seed), attempts=40)

    return {
        "Steepest Ascent": lambda p, s, trace=None: steepest_ascent(
            p, init(p, s), seed=s, max_iters=args.max_iters, trace=trace),
        f"Sideways (max={args.max_sideways})": lambda p, s, trace=None: sideways_move(
            p, init(p, s), seed=s, max_sideways=args.max_sideways, max_iters=args.max_iters, trace=trace),
        "Simulated Annealing": lambda p, s, trace=None: simulated_annealing(
            p, init(p, s), seed=s, init_temp=args.sa_temp, cooling_rate=args.sa_cooling,
            stopping_temp=args.sa_stop, trace=trace),
        "Genetic Algorithm": lambda p, s, trace=None: genetic_algorithm(
            p, population_size=args.population, generations=args.generations, seed=s, trace=trace),
    }


def cohens_d(a, b) -> float:
    sa, sb = statistics.pvariance(a), statistics.pvariance(b)
    pooled = ((sa + sb) / 2) ** 0.5
    return (statistics.fmean(a) - statistics.fmean(b)) / pooled if pooled else 0.0


def bootstrap_ci(vals, n=2000, seed=0):
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(vals, k=len(vals))) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n)]


def stats_report(runs: dict, ub: float) -> str:
    try:
        from scipy.stats import mannwhitneyu
    except Exception:
        mannwhitneyu = None
    lines = ["=== Statistik per algoritma (value akhir) ===",
             f"{'Algoritma':26s}{'mean':>9}{'median':>9}{'std':>8}{'CI95 bawah':>12}{'CI95 atas':>11}{'CV %':>7}{'gap UB %':>10}"]
    for name, rs in runs.items():
        v = [r.final_value for r in rs]
        lo, hi = bootstrap_ci(v)
        mean = statistics.fmean(v)
        cv = 100 * statistics.pstdev(v) / mean if mean else 0
        lines.append(f"{name:26s}{mean:>9.1f}{statistics.median(v):>9.1f}{statistics.pstdev(v):>8.1f}"
                     f"{lo:>12.1f}{hi:>11.1f}{cv:>7.1f}{100 * (ub - mean) / ub:>10.1f}")
    lines += ["", "=== Perbandingan berpasangan (A vs B) ===",
              f"{'A':26s}{'B':26s}{'selisih mean':>14}{'Cohen d':>11}{'p (Mann-Whitney)':>18}"]
    for (na, ra), (nb, rb) in itertools.combinations(runs.items(), 2):
        a, b = [r.final_value for r in ra], [r.final_value for r in rb]
        if mannwhitneyu and len(a) > 1 and len(b) > 1 and (len(set(a)) > 1 or len(set(b)) > 1 or a[0] != b[0]):
            try:
                p = f"{mannwhitneyu(a, b, alternative='two-sided').pvalue:.4f}"
            except ValueError:
                p = "n/a"
        else:
            p = "n/a (scipy ga ada)" if not mannwhitneyu else "n/a"
        lines.append(f"{na:26s}{nb:26s}{statistics.fmean(a) - statistics.fmean(b):>14.1f}{cohens_d(a, b):>11.2f}{p:>18}")
    lines += ["", "Catatan: p < 0.05 -> perbedaan antar algoritma signifikan secara statistik. |d| ~0.2 kecil, ~0.5 sedang, >=0.8 besar."]
    return "\n".join(lines)


def summarize(runs: dict, ub: float) -> str:
    head = (f"{'Algoritma':26s}{'n':>3}{'mean':>9}{'std':>8}{'best':>7}{'worst':>7}"
            f"{'gap UB%':>9}{'iter':>8}{'durasi(s)':>11}{'valid':>8}")
    lines = [head, "-" * len(head)]
    for name, rs in runs.items():
        vals = [r.final_value for r in rs]
        valid = sum(is_feasible(r.final_state) for r in rs)
        lines.append(f"{name:26s}{len(rs):>3}{statistics.fmean(vals):>9.1f}{statistics.pstdev(vals):>8.1f}"
                     f"{max(vals):>7}{min(vals):>7}{100 * (ub - statistics.fmean(vals)) / ub:>9.1f}"
                     f"{statistics.fmean(getattr(r, 'iterations', 0) for r in rs):>8.0f}"
                     f"{statistics.fmean(r.duration for r in rs):>11.3f}{valid:>5}/{len(rs)}")
    return "\n".join(lines)


def save_csv(runs: dict, path: Path, ub: float) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["algorithm", "seed", "initial_value", "final_value", "gap_ub_pct", "duration_sec",
                    "iterations", "stop_reason", "feasible"])
        for name, rs in runs.items():
            for r in rs:
                w.writerow([name, r.seed, r.initial_value, r.final_value, round(100 * (ub - r.final_value) / ub, 2),
                            round(r.duration, 4), getattr(r, "iterations", ""),
                            getattr(r, "stop_reason", "generations_done"), is_feasible(r.final_state)])


# ---------------------------------------------------------------- suite

def suite_main(problem, args, out: Path, ub: float, seeds: list[int]) -> dict:
    runs = {}
    for name, fn in build_algorithms(args).items():
        print(f"  menjalankan {name} ...")
        runs[name] = [fn(problem, s) for s in seeds]
    table = summarize(runs, ub)
    st = stats_report(runs, ub)
    print("\n" + table + "\n")
    (out / "summary.txt").write_text(table + "\n", encoding="utf-8")
    (out / "stats.txt").write_text(st + "\n", encoding="utf-8")
    save_csv(runs, out / "results.csv", ub)

    viz.plot_problem_overview(problem, out / "01_instance.png")
    viz.plot_convergence(runs, out / "02_convergence.png")
    viz.plot_distribution(runs, out / "03_distribution.png", ub)
    viz.plot_gap(runs, ub, out / "04_gap.png")
    viz.plot_improvement(runs, out / "05_improvement.png")
    viz.plot_time_vs_value(runs, out / "06_time_vs_value.png")
    viz.plot_ranking(runs, out / "07_ranking.png")
    viz.plot_hc_stats(runs, out / "08_hc_stats.png")
    viz.plot_sa_stats(runs, out / "08b_sa_stats.png")
    viz.plot_best_layouts(runs, out / "09_best_layouts.png")
    for name, rs in runs.items():
        best = max(rs, key=lambda r: r.final_value)
        viz.plot_state_detail(best.final_state, out / f"10_detail_{safe(name)}.png", f"{name} (seed {best.seed}) - state akhir terbaik")
        viz.plot_run(best, out / f"11_run_{safe(name)}.png", f"{name} (seed {best.seed})")
    return runs


def suite_ga(problem, args, out: Path, seeds: list[int]) -> None:
    def runga(**kw):
        base = dict(population_size=args.population, generations=args.generations)
        base.update(kw)
        return [genetic_algorithm(problem, seed=s, **base).final_value for s in seeds]

    grid = {
        "Populasi": ("population_size", [20, 50, 100]),
        "Generasi": ("generations", [50, 150, 300]),
        "Crossover rate": ("crossover_rate", [0.5, 0.7, 0.9]),
        "Mutation rate": ("mutation_rate", [0.1, 0.5, 0.9]),
        "Elite size": ("elite_size", [0, 2, 5]),
        "Ukuran turnamen": ("tournament_k", [2, 3, 5]),
    }
    sweeps = {}
    for title, (key, values) in grid.items():
        sweeps[title] = {str(v): runga(**{key: v}) for v in values}
        print(f"  sweep {title} selesai")
    viz.plot_param_sweep(sweeps, out / "20_ga_sweep.png", suptitle="Sensitivitas parameter Genetic Algorithm")

    pops, muts = [20, 50, 100], [0.1, 0.5, 0.9]
    mat = [[statistics.fmean(runga(population_size=p, mutation_rate=m)) for p in pops] for m in muts]
    viz.plot_heatmap(mat, [str(p) for p in pops], [str(m) for m in muts], out / "21_ga_heatmap.png",
                     "Interaksi ukuran populasi x mutation rate (GA)", "ukuran populasi", "mutation rate")


def suite_sideways(problem, args, out: Path, seeds: list[int]) -> None:
    data = {}
    for k in [0, 5, 20, 50, 100, 300]:
        data[k] = [sideways_move(problem, problem.random_state(random.Random(s), attempts=40), seed=s,
                                 max_sideways=k, max_iters=args.max_iters) for s in seeds]
        print(f"  max_sideways={k} selesai")
    viz.plot_sideways_sweep(data, out / "22_sideways_sweep.png")


def _scaled_problems(args, key: str, values: list):
    for v in values:
        if key == "n":
            yield v, generate_problem(n_vehicles=v, ship_w=args.ship_w, ship_l=args.ship_l, seed=args.problem_seed)
        else:
            yield v, generate_problem(n_vehicles=args.n_vehicles, ship_w=args.ship_w, ship_l=args.ship_l,
                                      capacity_ratio=v, seed=args.problem_seed)


def suite_series(args, out: Path, seeds: list[int], key: str) -> None:
    values = args.scale_n if key == "n" else [0.3, 0.45, 0.6, 0.75, 0.9]
    algos = build_algorithms(args)
    data = {name: {} for name in algos}
    ubs = {}
    for v, prob in _scaled_problems(args, key, values):
        ubs[v] = viz.upper_bound(prob)
        for name, fn in algos.items():
            data[name][v] = [fn(prob, s) for s in seeds]
        print(f"  {'n_kendaraan' if key == 'n' else 'rasio kapasitas'}={v} selesai")
    if key == "n":
        viz.plot_series_by_x(data, "jumlah kendaraan", out / "23_scalability.png", ubs, "Skalabilitas terhadap jumlah kendaraan")
    else:
        viz.plot_series_by_x(data, "rasio kapasitas (kapasitas / total berat)", out / "24_capacity.png", ubs,
                             "Pengaruh rasio kapasitas kapal")


def suite_trace(problem, args, out: Path) -> None:
    for name, fn in build_algorithms(args).items():
        trace: list = []
        fn(problem, 0, trace=trace)
        viz.plot_snapshots(trace, out / f"30_snapshots_{safe(name)}.png", name)
        viz.animate_trace(trace, out / f"31_anim_{safe(name)}.gif", name)
        print(f"  trace {name}: {len(trace)} state tercatat")


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description="Runner experiment + visualizer lengkap")
    ap.add_argument("--suites", default="main,trace", help=f"pisah koma, atau 'all'. Pilihan: {','.join(ALL_SUITES)}")
    ap.add_argument("--n-vehicles", type=int, default=25)
    ap.add_argument("--ship-w", type=int, default=10)
    ap.add_argument("--ship-l", type=int, default=20)
    ap.add_argument("--capacity", type=int, default=None, help="default: 60%% dari total berat")
    ap.add_argument("--problem-seed", type=int, default=1, help="seed pembuat problem (SAMA buat semua algoritma)")
    ap.add_argument("--runs", type=int, default=10, help="jumlah seed per algoritma (suite main)")
    ap.add_argument("--sweep-runs", type=int, default=5, help="jumlah seed per konfigurasi di suite sweep/scale/capacity")
    ap.add_argument("--scale-n", type=int, nargs="+", default=[10, 15, 20, 25, 30, 40])
    ap.add_argument("--max-iters", type=int, default=10000)
    ap.add_argument("--max-sideways", type=int, default=100)
    ap.add_argument("--sa-temp", type=float, default=50.0, help="suhu awal SA")
    ap.add_argument("--sa-cooling", type=float, default=0.999, help="cooling rate SA")
    ap.add_argument("--sa-stop", type=float, default=0.01, help="suhu berhenti SA")
    ap.add_argument("--population", type=int, default=50)
    ap.add_argument("--generations", type=int, default=300)
    ap.add_argument("--quick", action="store_true", help="preset kecil & cepat buat ngecek program")
    ap.add_argument("--pdf", action="store_true", help="simpan juga PDF vektor")
    ap.add_argument("--out", default="hasil")
    args = ap.parse_args()

    if args.quick:
        args.runs, args.sweep_runs, args.generations, args.population = 3, 2, 60, 30
        args.max_sideways, args.scale_n, args.sa_cooling = 20, [8, 12, 16], 0.99
    suites = ALL_SUITES if args.suites == "all" else [s.strip() for s in args.suites.split(",")]
    bad = [s for s in suites if s not in ALL_SUITES]
    if bad:
        raise SystemExit(f"Suite tidak dikenal: {bad}. Pilihan: {ALL_SUITES}")
    viz.SAVE_PDF = args.pdf

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    problem = generate_problem(n_vehicles=args.n_vehicles, ship_w=args.ship_w, ship_l=args.ship_l,
                               max_capacity=args.capacity, seed=args.problem_seed)
    ub = viz.upper_bound(problem)
    print(f"Problem: {args.n_vehicles} kendaraan, kapal {args.ship_w}x{args.ship_l}, "
          f"capacity={problem.ship.max_capacity}, batas atas value={ub:.1f}")
    seeds, sseeds = list(range(args.runs)), list(range(args.sweep_runs))

    for suite in suites:
        print(f"\n[suite: {suite}]")
        if suite == "main":
            suite_main(problem, args, out, ub, seeds)
        elif suite == "ga":
            suite_ga(problem, args, out, sseeds)
        elif suite == "sideways":
            suite_sideways(problem, args, out, sseeds)
        elif suite == "scale":
            suite_series(args, out, sseeds, "n")
        elif suite == "capacity":
            suite_series(args, out, sseeds, "capacity")
        elif suite == "trace":
            suite_trace(problem, args, out)

    with open(out / "DAFTAR_GAMBAR.md", "w", encoding="utf-8") as f:
        f.write("# Daftar gambar & usulan caption\n\n")
        for i, (fn, cap) in enumerate(sorted(viz.CAPTIONS), start=1):
            f.write(f"{i}. `{fn}` - {cap}\n")
    print(f"\nSelesai. Hasil disimpan di: {out.resolve()}")


if __name__ == "__main__":
    main()