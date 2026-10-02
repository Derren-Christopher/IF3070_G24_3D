from __future__ import annotations

import random

from define import HORIZONTAL, VERTICAL, Placement, Problem, Ship, State, Vehicle, generate_problem


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
            return value.upper()
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
            placements[vid] = Placement(x, y, orientation)
        else:
            orientation = ask_choice(f"Orientasi default {vid} saat di luar kapal ({HORIZONTAL}/{VERTICAL})? ", [HORIZONTAL, VERTICAL])
            placements[vid] = Placement(None, None, orientation)
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
    for vehicle in problem.vehicles.values():
        print(f"- {vehicle.id}: ukuran={vehicle.w}x{vehicle.l}, fee={vehicle.fee}, weight={vehicle.weight}")


def print_final_vehicle_positions(state: State) -> None:
    print("\n=== Detail penempatan akhir ===")
    for vid, placement in state.placements.items():
        if placement.placed:
            print(f"- {vid}: x={placement.x}, y={placement.y}, orientation={placement.orientation}")
        else:
            print(f"- {vid}: diluar kapal")


def print_ship_matrix(state: State, title: str = "=== Matriks penempatan di kapal ===") -> None:
    ship = state.problem.ship
    matrix = [["." for _ in range(ship.l)] for _ in range(ship.w)]

    for vid, placement in state.placements.items():
        if not placement.placed:
            continue
        vehicle = state.problem.vehicles[vid]
        dx, dy = state.problem.dims(vehicle, placement.orientation)
        for x in range(placement.x, placement.x + dx):
            for y in range(placement.y, placement.y + dy):
                if 0 <= x < ship.w and 0 <= y < ship.l:
                    matrix[x][y] = vid

    print(f"\n{title}")
    print("Kolom = y / baris = x")
    header = "    " + " ".join(f"{i:>3}" for i in range(ship.l))
    print(header)
    for i, row in enumerate(matrix):
        cells = " ".join(f"{cell:>3}" if cell != "." else "  ." for cell in row)
        print(f"{i:>2}: {cells}")


def print_step_report(problem: Problem, initial_state: State, algorithm: str, max_iters: int, max_sideways: int = 0, show_detail: bool = True) -> None:
    state = initial_state
    history = [state.value]
    sideways_total = 0
    sideways_streak = 0
    evaluated = 0
    stop_reason = "max_iterations"

    print("\n=== Laporan iterasi ===")
    print(f"Algoritma: {algorithm}")
    print(f"State awal: value={state.value}, inside={state.inside_ids()}, outside={state.outside_ids()}")

    for it in range(1, max_iters + 1):
        current_value = state.value
        candidates: list[tuple[object, int]] = []

        for move, val in problem.feasible_neighbors(state):
            evaluated += 1
            if val < current_value:
                continue
            candidates.append((move, val))

        if not candidates:
            stop_reason = "local_optimum"
            print(f"Iterasi {it}: tidak ada move yang valid / lebih baik.")
            break

        candidates.sort(key=lambda item: item[1], reverse=True)
        best_value = candidates[0][1]
        best_moves = [move for move, val in candidates if val == best_value]
        chosen_move = best_moves[0]

        if show_detail:
            print(f"\nIterasi {it} - current_value={current_value}")
            print("Semua candidate yang layak:")
            for move, val in candidates:
                marker = "<- selected" if move is chosen_move else ""
                print(f"  - {move.kind}: {move.desc} => value {val}{marker}")

        if algorithm == "steepest":
            if best_value > current_value:
                step_type = "naik"
                state = state.apply(chosen_move)
                history.append(state.value)
                sideways_streak = 0
                if show_detail:
                    print(f"Keputusan: {step_type} | move={chosen_move.kind} | desc={chosen_move.desc} | from {current_value} -> {state.value}")
            else:
                stop_reason = "local_optimum"
                print(f"Iterasi {it}: stop karena tidak ada kenaikan lagi.")
                break
        elif algorithm == "sideways":
            if best_value > current_value:
                step_type = "naik"
                state = state.apply(chosen_move)
                history.append(state.value)
                sideways_streak = 0
                if show_detail:
                    print(f"Keputusan: {step_type} | move={chosen_move.kind} | desc={chosen_move.desc} | from {current_value} -> {state.value}")
            elif best_value == current_value:
                if sideways_streak >= max_sideways:
                    stop_reason = "max_sideways_reached"
                    print(f"Iterasi {it}: stop karena max_sideways sudah tercapai ({max_sideways}).")
                    break
                state = state.apply(chosen_move)
                history.append(state.value)
                sideways_total += 1
                sideways_streak += 1
                if show_detail:
                    print(f"Keputusan: sideways | move={chosen_move.kind} | desc={chosen_move.desc} | from {current_value} -> {state.value}")
            else:
                stop_reason = "local_optimum"
                print(f"Iterasi {it}: stop karena tidak ada move yang lebih baik atau sama.")
                break
        else:
            raise ValueError(f"Algoritma tidak dikenal: {algorithm}")

    print("\n=== Ringkasan ===")
    print(f"final_value: {state.value}")
    print(f"iterations_done: {len(history) - 1}")
    print(f"history: {history}")
    print(f"sideways_moves: {sideways_total}")
    print(f"stop_reason: {stop_reason}")
    print(f"neighbors_evaluated: {evaluated}")


def main() -> None:
    print("=== Program Main Hill Climbing ===")
    print("Pilih mode eksekusi:")
    print("1. DEBUG DETAIL")
    print("   -> Cek logika, lihat semua candidate move, cari bug di tiap iterasi")
    print("2. SUMMARY")
    print("   -> Lihat hasil utama tanpa terlalu banyak detail")
    print("3. QUICK RUN")
    print("   -> Test cepat dan langsung lihat final result")

    mode_choice = ask_choice("Pilih mode [1/2/3]: ", ["1", "2", "3"])
    mode = "debug" if mode_choice == "1" else "summary" if mode_choice == "2" else "quick"

    print("\n=== Program Main Hill Climbing ===")
    print("Pilih algoritma:")
    print("1. Steepest Ascent")
    print("   -> Ambil move terbaik yang lebih baik dari state sekarang")
    print("2. Sideways Move")
    print("   -> Boleh ambil move yang sama bagusnya, lalu lanjut sampai batas sideways")
    choice = ask_choice("Pilih algoritma [1/2]: ", ["1", "2"])
    algorithm = "steepest" if choice == "1" else "sideways"

    n_vehicles = ask_int("Jumlah kendaraan: ", 1)
    ship_w = ask_int("Lebar kapal: ", 1)
    ship_l = ask_int("Panjang kapal: ", 1)
    max_capacity = ask_int("Max capacity kapal (berat maximum yang bisa ditampung): ", 1)
    seed = ask_int("Seed: ", 0)
    max_iters = ask_int("Max iterasi: ", 1)
    max_sideways = ask_int("Max sideways (untuk sideways): ", 0) if algorithm == "sideways" else 0

    print("\nPilih cara membuat kendaraan:")
    print("R. RANDOM")
    print("   -> Ukuran, fee, dan berat dibuat otomatis secara acak")
    print("M. MANUAL")
    print("   -> Masukkan ukuran, fee, dan berat satu per satu")
    vehicle_mode = ask_choice("Pilih cara buat kendaraan [R/M]: ", ["R", "M"])

    if mode == "debug":
        show_detail = True
        show_matrix = True
    elif mode == "summary":
        show_detail = False
        show_matrix = True
    else:
        show_detail = False
        show_matrix = False

    if vehicle_mode == "R":
        problem = generate_problem(n_vehicles=n_vehicles, ship_w=ship_w, ship_l=ship_l, max_capacity=max_capacity, seed=seed)
        total_weight = sum(vehicle.weight for vehicle in problem.vehicles.values())
        print(f"\nProblem dibuat: {len(problem.ids)} kendaraan, kapal {ship_w}x{ship_l}, capacity={problem.ship.max_capacity}")
        print(f"Total berat kendaraan yang dibuat: {total_weight}")
        print("Ukuran kendaraan, fee, dan berat dibuat otomatis secara acak berdasarkan seed.")
    else:
        vehicles = build_manual_vehicles(n_vehicles)
        problem = Problem(Ship(ship_w, ship_l, max_capacity), vehicles)
        total_weight = sum(vehicle.weight for vehicle in problem.vehicles.values())
        print(f"\nProblem dibuat: {len(problem.ids)} kendaraan, kapal {ship_w}x{ship_l}, capacity={problem.ship.max_capacity}")
        print(f"Total berat kendaraan yang dibuat: {total_weight}")
        print("Ukuran kendaraan, fee, dan berat diinput manual oleh user.")

    print_vehicle_list(problem)

    initial_state = random_state(problem, seed)
    print("State awal dibuat secara random.")

    print_step_report(problem, initial_state, algorithm, max_iters, max_sideways, show_detail)
    print_final_vehicle_positions(initial_state)
    if show_matrix:
        print_ship_matrix(initial_state)


if __name__ == "__main__":
    main()
