from __future__ import annotations
from define import Problem, Ship, State, Vehicle, generate_problem
from genetic_algorithm import GeneticResult, genetic_algorithm  




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




def ask_rate(prompt: str, default: float) -> float:
    while True:
        raw = input(f"{prompt} [default {default}]: ").strip()
        if raw == "":
            return default
        try:
            value = float(raw)
            if 0 <= value <= 1:
                return value
            print("Nilai harus di antara 0 dan 1.")
        except ValueError:
            print("Input harus angka.")




def ask_choice(prompt: str, options: list[str]) -> str:
    while True:
        value = input(prompt).strip().upper()
        if value in [opt.upper() for opt in options]:
            return value
        print(f"Pilih salah satu: {', '.join(options)}")




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




def verify_result(result: GeneticResult) -> list[tuple[str, bool]]:
    """Invarian yang harus selalu benar, dihitung independen dari kode GA."""
    final = result.final_state
    problem = final.problem
    inside = [vid for vid, p in final.placements.items() if p.placed]
    hb = result.history_best
    return [
        ("State akhir valid (tidak numpuk/keluar/overweight)", is_feasible(final)),
        ("Value == jumlah fee kendaraan di dalam", final.value == sum(problem.vehicles[i].fee for i in inside)),
        ("Berat == jumlah berat kendaraan di dalam", final.weight == sum(problem.vehicles[i].weight for i in inside)),
        ("history_best tidak pernah turun", all(a <= b for a, b in zip(hb, hb[1:]))),
        ("history_best[0] == value awal", hb[0] == result.initial_value),
        ("history_best[-1] == value akhir", hb[-1] == result.final_value),
        ("Panjang history == generasi + 1", len(hb) == result.generations + 1 == len(result.history_avg)),
        ("Value akhir >= value awal", result.final_value >= result.initial_value),
    ]




def sample_list(data: list, n: int = 20) -> list:
    """Ambil n titik merata dari list panjang biar output debug ga kebanyakan."""
    if len(data) <= n:
        return data
    step = len(data) / n
    return [data[int(i * step)] for i in range(n)] + [data[-1]]




def print_result(result: GeneticResult, show_matrix: bool, show_history: bool) -> None:
    final = result.final_state  # individu terbaik sepanjang pencarian
    if show_matrix:
        print_ship_matrix(result.initial_state, "Matriks geladak: STATE AWAL (terbaik populasi awal)")
    print_vehicle_positions(final, "Detail penempatan: STATE AKHIR (terbaik)")
    if show_matrix:
        print_ship_matrix(final, "Matriks geladak: STATE AKHIR (terbaik)")


    print("\n=== Ringkasan ===")
    print(f"Algoritma           : {result.algorithm}")
    print(f"Seed                : {result.seed}")
    print(f"Value awal -> akhir : {result.initial_value} -> {result.final_value}")
    print(f"Ukuran populasi     : {result.population_size}")
    print(f"Generasi            : {result.generations}")
    print(f"Rata-rata populasi  : {result.history_avg[0]:.3f} -> {result.history_avg[-1]:.3f}")
    print("Parameter           :")
    for key, val in result.params.items():
        print(f"  - {key}: {val}")
    print(f"Durasi              : {result.duration:.4f} detik")
    print(f"Di dalam kapal      : {final.inside_ids()}")
    print(f"Di luar kapal       : {final.outside_ids()}")


    print("\n=== Validasi otomatis ===")
    checks = verify_result(result)
    for name, ok in checks:
        print(f"[{'OK' if ok else 'GAGAL'}] {name}")
    print(f"State akhir valid   : {is_feasible(final)}")


    if show_history:
        print(f"\nHistory best (disampel) : {sample_list(result.history_best)}")
        print(f"History avg (disampel)  : {[round(a, 2) for a in sample_list(result.history_avg)]}")




def main() -> None:
    print("=== Program Main Genetic Algorithm ===")
    print("Pilih mode output:")
    print("1. DEBUG   -> semua detail + matriks awal & akhir + history")
    print("2. SUMMARY -> ringkasan + matriks awal & akhir")
    print("3. QUICK   -> ringkasan saja")
    mode_choice = ask_choice("Pilih mode [1/2/3]: ", ["1", "2", "3"])
    show_matrix = mode_choice in {"1", "2"}
    show_history = mode_choice == "1"


    n_vehicles = ask_int("Jumlah kendaraan (min 2, karena mutasi Swap butuh 2 kendaraan): ", 2)
    ship_w = ask_int("Lebar kapal: ", 1)
    ship_l = ask_int("Panjang kapal: ", 1)
    max_capacity = ask_int("Max capacity kapal (berat maksimum): ", 1)
    seed = ask_int("Seed: ", 0)


    print("\nParameter Genetic Algorithm (Enter untuk pakai default):")
    population_size = ask_int_default("Ukuran populasi", 50, 2)
    generations = ask_int_default("Jumlah generasi", 300, 1)
    crossover_rate = ask_rate("Crossover rate (0-1)", 0.9)
    mutation_rate = ask_rate("Mutation rate (0-1)", 0.9)
    mutation_steps = ask_int_default("Maks mutasi per anak", 6, 1)
    elite_size = ask_int_default("Elite size", 2, 0)
    elite_size = min(elite_size, population_size)
    tournament_k = ask_int_default("Ukuran turnamen", 2, 1)
    init_attempts = ask_int_default("Percobaan menaruh kendaraan saat bikin state awal", 40, 1)


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


    print("\nPopulasi awal dibuat secara random di dalam algoritma.")
    result = genetic_algorithm(problem, population_size=population_size, generations=generations,
                               seed=seed, crossover_rate=crossover_rate, mutation_rate=mutation_rate,
                               mutation_steps=mutation_steps, elite_size=elite_size,
                               tournament_k=tournament_k, init_attempts=init_attempts)
    print_result(result, show_matrix, show_history)




if __name__ == "__main__":
    main()