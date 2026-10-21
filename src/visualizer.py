from __future__ import annotations

import statistics
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.animation import FuncAnimation, PillowWriter

from define import VERTICAL

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 200, "font.size": 10, "axes.titlesize": 11,
    "axes.titleweight": "bold", "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "legend.frameon": False,
})

ALGO_COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860", "#DA8BC3", "#8C8C8C"]
CAPTIONS: list[tuple[str, str]] = []   
SAVE_PDF = False                      

def _save(fig, path, caption: str = "") -> None:
    path = Path(path)
    fig.savefig(path, bbox_inches="tight")
    if SAVE_PDF:
        fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    CAPTIONS.append((path.name, caption))

def _acolor(k: int) -> str:
    return ALGO_COLORS[k % len(ALGO_COLORS)]

def _vcolor(problem, vid: str):
    return plt.get_cmap("tab20")(problem.ids.index(vid) % 20)

def _boxplot(ax, data, names, colors):
    try:
        bp = ax.boxplot(data, tick_labels=names, patch_artist=True, showmeans=True, widths=0.55)
    except TypeError:  # matplotlib lama
        bp = ax.boxplot(data, labels=names, patch_artist=True, showmeans=True, widths=0.55)
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.45)
    for med in bp["medians"]:
        med.set_color("black")
    return bp

def get_history(result) -> list[int]:
    """Kurva 'terbaik sejauh ini': SA -> best_history, HC -> history, GA -> history_best."""
    for attr in ("best_history", "history", "history_best"):
        h = getattr(result, attr, None)
        if h is not None:
            return list(h)
    raise AttributeError("result ga punya history/best_history/history_best")

def is_population_based(results) -> bool:
    return hasattr(results[0], "history_avg")

def pad_histories(histories):
    n = max(len(h) for h in histories)
    return [h + [h[-1]] * (n - len(h)) for h in histories]

def mean_curve(histories):
    padded = pad_histories(histories)
    return ([statistics.fmean(c) for c in zip(*padded)], [statistics.pstdev(c) for c in zip(*padded)])

def state_metrics(state) -> dict:
    problem, ship = state.problem, state.problem.ship
    inside = state.inside_ids()
    area = 0
    for vid in inside:
        dx, dy = problem.dims(problem.vehicles[vid], state.placements[vid].orientation)
        area += dx * dy
    deck = ship.w * ship.l
    total_fee = sum(v.fee for v in problem.vehicles.values())
    return {
        "inside": len(inside), "outside": len(problem.ids) - len(inside),
        "area_used": area, "deck_area": deck, "area_util": 100 * area / deck,
        "weight_util": 100 * state.weight / ship.max_capacity if ship.max_capacity else 0.0,
        "fee": state.value, "fee_pct": 100 * state.value / total_fee if total_fee else 0.0,
    }

def upper_bound(problem) -> float:
    def frac(items, cap): 
        total = 0.0
        for fee, size in sorted(items, key=lambda t: t[0] / t[1] if t[1] > 0 else float("inf"), reverse=True):
            if size <= 0:
                total += fee
            elif cap >= size:
                total += fee
                cap -= size
            else:
                total += fee * cap / size
                break
        return total
    vs = list(problem.vehicles.values())
    ub_w = frac([(v.fee, v.weight) for v in vs], problem.ship.max_capacity)
    ub_a = frac([(v.fee, v.w * v.l) for v in vs], problem.ship.w * problem.ship.l)
    return min(ub_w, ub_a, sum(v.fee for v in vs))

#KAPAL & KENDARAAN

def draw_ship(ax, state, title: str = "", labels: bool = True) -> None:
    problem, ship = state.problem, state.problem.ship
    ax.add_patch(Rectangle((0, 0), ship.l, ship.w, facecolor="#f4f6f8", edgecolor="black", linewidth=2, zorder=0))
    ax.set_xlim(-0.5, ship.l + 0.5)
    ax.set_ylim(ship.w + 0.5, -0.5)
    ax.set_aspect("equal")
    ax.set_xticks(range(0, ship.l + 1, max(1, ship.l // 10)))
    ax.set_yticks(range(0, ship.w + 1, max(1, ship.w // 10)))
    ax.grid(True, color="#cfd4da", linewidth=0.5)
    ax.set_axisbelow(True)
    for vid in problem.ids:
        p = state.placements[vid]
        if not p.placed:
            continue
        v = problem.vehicles[vid]
        dx, dy = problem.dims(v, p.orientation)
        ax.add_patch(Rectangle((p.y, p.x), dy, dx, facecolor=_vcolor(problem, vid), edgecolor="black",
                               linewidth=1.1, alpha=0.9, zorder=2, hatch="///" if p.orientation == VERTICAL else None))
        if labels:
            fs = 7 if min(dx, dy) >= 2 else 5.5
            ax.text(p.y + dy / 2, p.x + dx / 2, f"{vid}\n{v.fee}", ha="center", va="center", fontsize=fs, zorder=3,
                    bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.55))
    m = state_metrics(state)
    ax.set_title(f"{title}\nfee={m['fee']} | berat={state.weight}/{ship.max_capacity} | "
                 f"luas terpakai={m['area_util']:.0f}% | di luar={m['outside']}", fontsize=9)
    outside = state.outside_ids()
    ax.set_xlabel("y (panjang geladak)\n" + textwrap.fill("Di luar kapal: " + (", ".join(outside) or "-"), 70),
                  fontsize=8)
    ax.set_ylabel("x (lebar geladak)")

def plot_problem_overview(problem, path) -> None:
    ship = problem.ship
    vs = list(problem.vehicles.values())
    ub = upper_bound(problem)
    fig = plt.figure(figsize=(15, 9))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1])

    ax = fig.add_subplot(gs[0, 0])
    maxw, x0, y0, rowh = 34, 0, 0, 0
    for v in vs:
        if x0 + v.l > maxw:
            x0, y0, rowh = 0, y0 + rowh + 1, 0
        ax.add_patch(Rectangle((x0, y0), v.l, v.w, facecolor=_vcolor(problem, v.id), edgecolor="black", lw=1))
        ax.text(x0 + v.l / 2, y0 + v.w / 2, f"{v.id}\n{v.w}x{v.l}", ha="center", va="center", fontsize=6.5)
        x0 += v.l + 1
        rowh = max(rowh, v.w)
    ax.set_xlim(-0.5, maxw + 0.5)
    ax.set_ylim(y0 + rowh + 1, -0.5)
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_title("(a) Katalog kendaraan (bentuk berskala, w x l)")
    ax.set_xticks([])
    ax.set_yticks([])

    ax = fig.add_subplot(gs[0, 1])
    order = sorted(vs, key=lambda v: v.fee, reverse=True)
    ax.bar([v.id for v in order], [v.fee for v in order], color=[_vcolor(problem, v.id) for v in order],
           edgecolor="black", linewidth=0.5)
    ax.set_title("(b) ShippingFee tiap kendaraan")
    ax.set_ylabel("fee")
    plt.setp(ax.get_xticklabels(), rotation=90, fontsize=7)

    ax = fig.add_subplot(gs[1, 0])
    ax.scatter([v.weight for v in vs], [v.fee for v in vs], s=[v.w * v.l * 18 for v in vs],
               c=[_vcolor(problem, v.id) for v in vs], edgecolor="black", alpha=0.85)
    for v in vs:
        ax.annotate(v.id, (v.weight, v.fee), fontsize=6.5, ha="center", va="center")
    ax.set_xlabel("berat")
    ax.set_ylabel("fee")
    ax.set_title("(c) Fee vs berat (ukuran titik = luas kendaraan)")

    ax = fig.add_subplot(gs[1, 1])
    ax.axis("off")
    tw, ta, tf = sum(v.weight for v in vs), sum(v.w * v.l for v in vs), sum(v.fee for v in vs)
    rows = [
        ("Ukuran geladak (lebar x panjang)", f"{ship.w} x {ship.l}  (luas {ship.w * ship.l})"),
        ("Kapasitas berat maksimum", f"{ship.max_capacity}"),
        ("Jumlah kendaraan", f"{len(vs)}"),
        ("Total berat semua kendaraan", f"{tw}  ({100 * tw / ship.max_capacity:.0f}% dari kapasitas)"),
        ("Total luas semua kendaraan", f"{ta}  ({100 * ta / (ship.w * ship.l):.0f}% dari luas geladak)"),
        ("Total fee semua kendaraan", f"{tf}"),
        ("Batas atas value (relaksasi)", f"{ub:.1f}"),
    ]
    t = ax.table(cellText=[[a, b] for a, b in rows], colLabels=["Parameter", "Nilai"], loc="center",
                 cellLoc="left", colWidths=[0.5, 0.5])
    t.auto_set_font_size(False)
    t.set_fontsize(10)
    t.scale(1, 1.8)
    ax.set_title("(d) Ringkasan instance")
    fig.suptitle("Gambaran umum instance masalah", fontsize=14, fontweight="bold")
    fig.tight_layout()
    _save(fig, path, "Gambaran instance: katalog kendaraan, distribusi fee, hubungan fee-berat, dan ringkasan kapal.")


def plot_state_detail(state, path, title: str = "State") -> None:
    problem = state.problem
    m = state_metrics(state)
    fig = plt.figure(figsize=(15, 6.5))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.5, 1], height_ratios=[2.2, 1])
    draw_ship(fig.add_subplot(gs[:, 0]), state, title)

    ax = fig.add_subplot(gs[0, 1])
    order = sorted(problem.ids, key=lambda i: problem.vehicles[i].fee)
    cols = [_vcolor(problem, i) if state.placements[i].placed else "#c8c8c8" for i in order]
    ax.barh(order, [problem.vehicles[i].fee for i in order], color=cols, edgecolor="black", linewidth=0.4)
    ax.set_title("Fee kendaraan (abu-abu = di luar kapal)", fontsize=10)
    ax.tick_params(axis="y", labelsize=6.5)
    ax.set_xlabel("fee")

    ax = fig.add_subplot(gs[1, 1])
    labels = ["Luas geladak", "Kapasitas berat", "Fee dari total"]
    vals = [m["area_util"], m["weight_util"], m["fee_pct"]]
    ax.barh(labels, vals, color=["#4C72B0", "#DD8452", "#55A868"])
    for i, v in enumerate(vals):
        ax.text(min(v + 1, 92), i, f"{v:.1f}%", va="center", fontsize=9)
    ax.set_xlim(0, 105)
    ax.set_title("Utilisasi", fontsize=10)
    fig.tight_layout()
    _save(fig, path, f"Detail state: {title}.")

def plot_run(result, path, title: str = "") -> None:
    """Satu run: layout awal, layout akhir, dan kurva history."""
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.2), gridspec_kw={"width_ratios": [1.2, 1.2, 1]})
    draw_ship(axes[0], result.initial_state, "State awal")
    draw_ship(axes[1], result.final_state, "State akhir")
    hist = get_history(result)
    cur = getattr(result, "history", None) if hasattr(result, "best_history") else None
    if cur is not None:  # SA: nilai state saat ini (naik-turun karena terima move buruk)
        axes[2].plot(cur, color="#9ab", alpha=0.6, linewidth=0.7, label="state saat ini")
    axes[2].plot(hist, color=ALGO_COLORS[0], label="terbaik")
    avg = getattr(result, "history_avg", None)
    if avg is not None:
        axes[2].plot(avg, color=ALGO_COLORS[1], linestyle="--", label="rata-rata populasi")
    axes[2].set_xlabel("iterasi / generasi")
    axes[2].set_ylabel("value (total fee)")
    axes[2].set_title("Riwayat value")
    axes[2].legend()
    fig.suptitle(title or getattr(result, "algorithm", ""), fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, path, f"Satu run {title or getattr(result, 'algorithm', '')}: layout awal, layout akhir, riwayat value.")

def plot_best_layouts(runs, path) -> None:
    n = len(runs)
    fig, axes = plt.subplots(1, n, figsize=(6.2 * n, 5.6), squeeze=False)
    for ax, (name, results) in zip(axes[0], runs.items()):
        best = max(results, key=lambda r: r.final_value)
        draw_ship(ax, best.final_state, f"{name} (seed {best.seed})")
    fig.tight_layout()
    _save(fig, path, "Layout akhir dari run terbaik masing-masing algoritma (arsir = orientasi Vertical).")

def plot_snapshots(trace, path, title: str = "", n: int = 6) -> None:
    n = min(n, len(trace))
    idx = sorted({round(i * (len(trace) - 1) / max(1, n - 1)) for i in range(n)})
    cols = 3
    rows = -(-len(idx) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 5.4 * rows), squeeze=False)
    for ax in axes.flat:
        ax.axis("off")
    for ax, i in zip(axes.flat, idx):
        step, st = trace[i]
        ax.axis("on")
        draw_ship(ax, st, f"Langkah {step}", labels=True)
    fig.suptitle(title or "Perkembangan layout selama pencarian", fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, path, f"Snapshot perkembangan layout geladak selama pencarian ({title}).")

def animate_trace(trace, path, title: str = "", max_frames: int = 40, fps: int = 4) -> None:
    if len(trace) > max_frames:
        idx = sorted({round(i * (len(trace) - 1) / (max_frames - 1)) for i in range(max_frames)})
        trace = [trace[i] for i in idx]
    fig, ax = plt.subplots(figsize=(8, 5.6))

    def update(k):
        ax.clear()
        step, st = trace[k]
        draw_ship(ax, st, f"{title} - langkah {step}")
        return []

    anim = FuncAnimation(fig, update, frames=len(trace), blit=False)
    anim.save(str(path), writer=PillowWriter(fps=fps))
    plt.close(fig)
    CAPTIONS.append((Path(path).name, f"Animasi perkembangan layout ({title}); buat presentasi, bukan laporan tertulis."))


def plot_convergence(runs, path) -> None:
    single = {n: r for n, r in runs.items() if not is_population_based(r)}
    pop = {n: r for n, r in runs.items() if is_population_based(r)}
    panels = [p for p in (single, pop) if p]
    fig, axes = plt.subplots(1, len(panels), figsize=(7.5 * len(panels), 5), squeeze=False)
    k = 0
    for ax, group in zip(axes[0], panels):
        n_group = max(len(get_history(r)) for rs in group.values() for r in rs)  # semua kurva sepanjang yang terpanjang
        for name, results in group.items():
            hs = [get_history(r) for r in results]
            hs = [h + [h[-1]] * (n_group - len(h)) for h in hs]  # berhenti = value tetap
            mean, std = mean_curve(hs)
            xs = list(range(len(mean)))
            ax.plot(xs, mean, color=_acolor(k), label=f"{name}" + (" (terbaik)" if group is pop else ""))
            ax.fill_between(xs, [m - s for m, s in zip(mean, std)], [m + s for m, s in zip(mean, std)],
                            color=_acolor(k), alpha=0.15)
            if group is pop:
                amean, _ = mean_curve([list(map(float, r.history_avg)) for r in results])  # GA selalu sama panjang
                ax.plot(range(len(amean)), amean, color=_acolor(k), linestyle="--", alpha=0.8,
                        label=f"{name} (rata-rata populasi)")
            k += 1
        if group is not pop and n_group > 300:
            ax.set_xscale("symlog", linthresh=10)
        ax.set_xlabel("generasi" if group is pop else ("iterasi (skala symlog)" if n_group > 300 else "iterasi"))
        ax.set_ylabel("value (total fee)")
        ax.set_title("Algoritma berbasis populasi" if group is pop else "Algoritma satu-solusi (Hill Climbing/SA)")
        ax.legend(fontsize=8)
    fig.suptitle("Kurva konvergensi rata-rata antar seed (area = +-1 std)", fontweight="bold")
    fig.tight_layout()
    _save(fig, path, "Kurva konvergensi rata-rata value terbaik terhadap iterasi/generasi, area teduh = +-1 std antar seed.")


def plot_distribution(runs, path, ub: float | None = None) -> None:
    names = list(runs)
    finals = [[r.final_value for r in runs[n]] for n in names]
    durs = [[r.duration for r in runs[n]] for n in names]
    cols = [_acolor(i) for i in range(len(names))]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    _boxplot(axes[0], finals, names, cols)
    for i, vals in enumerate(finals, start=1):
        step = 0.3 / max(1, len(vals) - 1)
        axes[0].scatter([i - 0.15 + j * step for j in range(len(vals))], vals, s=14, color="black", alpha=0.6, zorder=3)
    if ub is not None:
        axes[0].axhline(ub, color="red", linestyle="--", linewidth=1)
        axes[0].text(0.55, ub, f" batas atas {ub:.0f}", color="red", va="bottom", fontsize=8)
    axes[0].set_title("Distribusi value akhir antar seed (segitiga = mean)")
    axes[0].set_ylabel("total fee")
    _boxplot(axes[1], durs, names, cols)
    axes[1].set_yscale("log")
    axes[1].set_title("Distribusi durasi eksekusi")
    axes[1].set_ylabel("detik (skala log)")
    for ax in axes:
        plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    fig.tight_layout()
    _save(fig, path, "Distribusi value akhir dan durasi eksekusi tiap algoritma pada seluruh seed.")

def plot_gap(runs, ub: float, path) -> None:
    names = list(runs)
    gaps = [[100 * (ub - r.final_value) / ub for r in runs[n]] for n in names]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(names, [statistics.fmean(g) for g in gaps], yerr=[statistics.pstdev(g) for g in gaps], capsize=5,
           color=[_acolor(i) for i in range(len(names))], alpha=0.85)
    for i, g in enumerate(gaps):
        ax.text(i, statistics.fmean(g) + statistics.pstdev(g) + 0.3, f"{statistics.fmean(g):.1f}%", ha="center", fontsize=9)
    ax.set_ylabel("gap ke batas atas (%) - makin kecil makin baik")
    ax.set_title("Gap terhadap batas atas relaksasi")
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    fig.tight_layout()
    _save(fig, path, "Gap relatif value akhir terhadap batas atas (relaksasi knapsack pecahan); error bar = std.")


def plot_improvement(runs, path) -> None:
    names = list(runs)
    ini = [statistics.fmean(r.initial_value for r in runs[n]) for n in names]
    fin = [statistics.fmean(r.final_value for r in runs[n]) for n in names]
    xs = range(len(names))
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    axes[0].bar([x - 0.2 for x in xs], ini, 0.4, label="awal", color="#b7c4d9")
    axes[0].bar([x + 0.2 for x in xs], fin, 0.4, label="akhir", color=[_acolor(i) for i in xs])
    axes[0].set_xticks(list(xs))
    axes[0].set_xticklabels(names, rotation=15, ha="right")
    axes[0].set_ylabel("rata-rata total fee")
    axes[0].set_title("Value awal vs akhir")
    axes[0].legend()
    gain = [100 * (f - i) / i if i else 0 for i, f in zip(ini, fin)]
    axes[1].bar(names, gain, color=[_acolor(i) for i in xs], alpha=0.85)
    for i, g in enumerate(gain):
        axes[1].text(i, g, f"{g:.0f}%", ha="center", va="bottom", fontsize=9)
    axes[1].set_ylabel("peningkatan (%)")
    axes[1].set_title("Peningkatan relatif dari state awal")
    plt.setp(axes[1].get_xticklabels(), rotation=15, ha="right")
    fig.tight_layout()
    _save(fig, path, "Rata-rata value state awal vs state akhir dan persentase peningkatannya.")


def plot_time_vs_value(runs, path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5.4))
    for k, (name, rs) in enumerate(runs.items()):
        ax.scatter([r.duration for r in rs], [r.final_value for r in rs], color=_acolor(k), alpha=0.5, s=22)
        ax.scatter(statistics.fmean(r.duration for r in rs), statistics.fmean(r.final_value for r in rs),
                   color=_acolor(k), marker="*", s=260, edgecolor="black", label=name, zorder=3)
    ax.set_xscale("log")
    ax.set_xlabel("durasi (detik, skala log)")
    ax.set_ylabel("value akhir (total fee)")
    ax.set_title("Trade-off kualitas solusi vs waktu komputasi")
    ax.legend()
    fig.tight_layout()
    _save(fig, path, "Trade-off value akhir vs durasi; titik = satu run, bintang = rata-rata algoritma.")

def plot_ranking(runs, path) -> None:
    names = list(runs)
    n_seeds = min(len(runs[n]) for n in names)
    counts = {n: [0] * len(names) for n in names}
    for s in range(n_seeds):
        vals = {n: runs[n][s].final_value for n in names}
        for n in names:
            rank = 1 + sum(1 for m in names if vals[m] > vals[n])
            counts[n][rank - 1] += 1
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    bottom = [0] * len(names)
    shades = ["#2e7d32", "#f9a825", "#c62828", "#6d4c41", "#546e7a"]
    for r in range(len(names)):
        vals = [counts[n][r] for n in names]
        ax.bar(names, vals, bottom=bottom, label=f"peringkat {r + 1}", color=shades[r % len(shades)], alpha=0.85)
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_ylabel("jumlah seed")
    ax.set_title("Frekuensi peringkat per seed (peringkat 1 = value tertinggi)")
    ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    fig.tight_layout()
    _save(fig, path, "Frekuensi peringkat tiap algoritma di seluruh seed (seri = peringkat sama).")


def plot_hc_stats(runs, path) -> None:
    hc = {n: r for n, r in runs.items() if hasattr(r[0], "sideways_moves")}
    if not hc:
        return
    names = list(hc)
    cols = [_acolor(i) for i in range(len(names))]
    fig, axes = plt.subplots(1, 4, figsize=(19, 4.6))
    _boxplot(axes[0], [[r.iterations for r in hc[n]] for n in names], names, cols)
    axes[0].set_title("Iterasi sampai berhenti")
    axes[1].bar(names, [statistics.fmean(r.neighbors_evaluated for r in hc[n]) for n in names], color=cols, alpha=0.85)
    axes[1].set_yscale("log")
    axes[1].set_title("Rata-rata tetangga dievaluasi")
    axes[2].bar(names, [statistics.fmean(r.sideways_moves for r in hc[n]) for n in names], color=cols, alpha=0.85)
    axes[2].set_title("Rata-rata langkah sideways")
    reasons = sorted({r.stop_reason for n in names for r in hc[n]})
    bottom = [0] * len(names)
    for j, reason in enumerate(reasons):
        vals = [sum(1 for r in hc[n] if r.stop_reason == reason) for n in names]
        axes[3].bar(names, vals, bottom=bottom, label=reason, color=plt.get_cmap("Set2")(j))
        bottom = [b + v for b, v in zip(bottom, vals)]
    axes[3].set_title("Alasan berhenti")
    axes[3].legend(fontsize=8)
    for ax in axes:
        plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    fig.tight_layout()
    _save(fig, path, "Statistik Hill Climbing: iterasi, tetangga dievaluasi, langkah sideways, dan alasan berhenti.")

def plot_param_sweep(sweeps: dict, path, ylabel: str = "value akhir rata-rata", suptitle: str = "") -> None:
    n = len(sweeps)
    cols = min(3, n)
    rows = -(-n // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(5.4 * cols, 4.2 * rows), squeeze=False)
    for ax in axes.flat:
        ax.axis("off")
    for ax, (title, groups) in zip(axes.flat, sweeps.items()):
        ax.axis("on")
        labels = list(groups)
        means = [statistics.fmean(v) for v in groups.values()]
        stds = [statistics.pstdev(v) for v in groups.values()]
        ax.errorbar(range(len(labels)), means, yerr=stds, marker="o", capsize=4, color=ALGO_COLORS[0], linewidth=1.8)
        for i, vals in enumerate(groups.values()):
            ax.scatter([i] * len(vals), vals, s=10, color="black", alpha=0.35)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels)
        ax.set_xlabel(title)
        ax.set_ylabel(ylabel)
        ax.set_title(f"Pengaruh {title}")
    fig.suptitle(suptitle or "Analisis sensitivitas parameter", fontweight="bold")
    fig.tight_layout()
    _save(fig, path, f"{suptitle or 'Analisis sensitivitas parameter'} (garis = mean +- std, titik = tiap seed).")

def plot_sideways_sweep(data: dict, path) -> None:
    keys = sorted(data)
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.4))
    specs = [("Value akhir", lambda r: r.final_value), ("Iterasi", lambda r: r.iterations),
             ("Durasi (detik)", lambda r: r.duration)]
    for ax, (ttl, fn) in zip(axes, specs):
        means = [statistics.fmean(fn(r) for r in data[k]) for k in keys]
        stds = [statistics.pstdev([fn(r) for r in data[k]]) for k in keys]
        ax.errorbar(range(len(keys)), means, yerr=stds, marker="o", capsize=4, color=ALGO_COLORS[1], linewidth=1.8)
        ax.set_xticks(range(len(keys)))
        ax.set_xticklabels([str(k) for k in keys])
        ax.set_xlabel("max sideways moves")
        ax.set_title(ttl)
    fig.suptitle("Pengaruh batas sideways move pada Hill Climbing", fontweight="bold")
    fig.tight_layout()
    _save(fig, path, "Pengaruh batas sideways move terhadap value akhir, jumlah iterasi, dan durasi (mean +- std).")


def plot_heatmap(matrix, xlabels, ylabels, path, title: str, xlabel: str = "", ylabel: str = "") -> None:
    fig, ax = plt.subplots(figsize=(1.4 * len(xlabels) + 3, 1.0 * len(ylabels) + 2.5))
    im = ax.imshow(matrix, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(xlabels)))
    ax.set_xticklabels(xlabels)
    ax.set_yticks(range(len(ylabels)))
    ax.set_yticklabels(ylabels)
    ax.grid(False)
    for i in range(len(ylabels)):
        for j in range(len(xlabels)):
            ax.text(j, i, f"{matrix[i][j]:.0f}", ha="center", va="center", fontsize=10)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label="value akhir rata-rata")
    fig.tight_layout()
    _save(fig, path, f"{title} (nilai di sel = rata-rata value akhir).")


def plot_series_by_x(data: dict, xlabel: str, path, ubs: dict | None = None, title: str = "") -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    for k, (name, by_x) in enumerate(data.items()):
        xs = sorted(by_x)
        def val(x, r):
            return 100 * r.final_value / ubs[x] if ubs else r.final_value
        m = [statistics.fmean(val(x, r) for r in by_x[x]) for x in xs]
        s = [statistics.pstdev([val(x, r) for r in by_x[x]]) for x in xs]
        axes[0].errorbar(xs, m, yerr=s, marker="o", capsize=3, color=_acolor(k), label=name)
        axes[1].plot(xs, [statistics.fmean(r.duration for r in by_x[x]) for x in xs], marker="o", color=_acolor(k), label=name)
    axes[0].set_ylabel("value akhir (% dari batas atas)" if ubs else "value akhir")
    axes[0].set_title("Kualitas solusi")
    axes[1].set_yscale("log")
    axes[1].set_ylabel("durasi rata-rata (detik, log)")
    axes[1].set_title("Waktu komputasi")
    for ax in axes:
        ax.set_xlabel(xlabel)
        ax.legend(fontsize=8)
    fig.suptitle(title, fontweight="bold")
    fig.tight_layout()
    _save(fig, path, f"{title} (mean +- std antar seed).")


def plot_sa_stats(runs, path) -> None:
    sa = [r for rs in runs.values() for r in rs if hasattr(r, "exp_log")]
    if not sa:
        return
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    r0 = sa[0]
    ax = axes[0, 0]
    ax.plot(r0.history, color="#9ab", linewidth=0.6, label="state saat ini")
    ax.plot(r0.best_history, color=ALGO_COLORS[3], linewidth=1.6, label="terbaik")
    ax.set_xlabel("iterasi")
    ax.set_ylabel("value")
    ax2 = ax.twinx()
    ax2.plot(r0.temp_history, color="black", linestyle="--", linewidth=1, label="suhu")
    ax2.set_ylabel("suhu T")
    ax2.set_yscale("log")
    ax2.grid(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="lower right")
    ax.set_title(f"(a) Value dan suhu (seed {r0.seed})")

    ax = axes[0, 1]
    xs, ys, cs = [], [], []
    for r in sa:
        for it, delta, prob in r.exp_log[:: max(1, len(r.exp_log) // 600)]:
            xs.append(r.temp_history[it - 1])
            ys.append(prob)
            cs.append(delta)
    sc = ax.scatter(xs, ys, c=cs, s=8, cmap="viridis", alpha=0.6)
    ax.set_xscale("log")
    ax.set_xlabel("suhu T (skala log)")
    ax.set_ylabel("peluang terima  e^(delta/T)")
    fig.colorbar(sc, ax=ax, label="delta (negatif = lebih buruk)")
    ax.set_title("(b) Peluang menerima move yang lebih buruk")

    ax = axes[1, 0]
    labels = [f"s{r.seed}" for r in sa]
    acc = [100 * r.accepted / max(1, r.neighbors_evaluated) for r in sa]
    worse = [100 * r.worse_accepted / max(1, r.neighbors_evaluated) for r in sa]
    ax.bar(labels, acc, label="diterima (semua)", color=ALGO_COLORS[0], alpha=0.8)
    ax.bar(labels, worse, label="diterima (lebih buruk)", color=ALGO_COLORS[1], alpha=0.9)
    ax.set_ylabel("% dari neighbor dievaluasi")
    ax.set_title("(c) Rasio penerimaan move per seed")
    ax.legend(fontsize=8)

    ax = axes[1, 1]
    ax.bar(labels, [r.stuck_count for r in sa], color=ALGO_COLORS[4], alpha=0.85)
    ax.set_ylabel("jumlah kejadian stuck")
    n_loc = sum(r.final_is_local_optimum for r in sa)
    ax.set_title(f"(d) Stuck di local optimum (state akhir local optimum: {n_loc}/{len(sa)} seed)")
    fig.suptitle("Analisis khusus Simulated Annealing", fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, path, "Analisis Simulated Annealing: suhu vs value, peluang terima move buruk, rasio penerimaan, dan stuck.")