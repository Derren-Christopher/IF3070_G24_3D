import math
import random
import time
from define import Placement, Move, HORIZONTAL, VERTICAL

def pick_neighbor(problem, state, rng):
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

def simulated_annealing(problem, beginning, init_temp,cooling_rate, stopping_temp, rng):
    start = time.time()
    current = beginning
    best = beginning
    T = init_temp
    iteration = 0
    consec_no_improve = 0
    stuck_count = 0
    stagnation_threshold = 50
    best_hist = [] #mencatat value terbaik di setiap iterasi
    current_hist = [] #mencatat nilai state di setiap iterasi
    exp_hist = [] #mencatat nilai e^(delta/T)

    while T > stopping_temp:
        result = pick_neighbor(problem, current, rng)

        if result is not None:
            move, neight_obj =  result
            delta = neight_obj - current.value

            if delta > 0:
                accept = True
            else:
                accept_prob = math.exp (delta/T)
                if delta < 0:
                    exp_hist.append((iteration, accept_prob))
                accept = rng.random() < accept_prob

            if accept:
                current = current.apply(move)
            
            if current.value > best.value:
                best = current
                consec_no_improve = 0
            else:
                consec_no_improve += 1
                if consec_no_improve >= stagnation_threshold:
                    stuck_count +=1
                    consec_no_improve=0
        
        best_hist.append(best.value)
        current_hist.append(current.value)
        T = T*cooling_rate
        iteration += 1

    duration = time.time() - start
    return best, best_hist, current_hist, exp_hist, stuck_count, iteration, duration

def show_graphics(best_hist, current_hist, exp_hist, judul=""):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    ax[0].plot(current_hist, label="Current", alpha=0.6)
    ax[0].plot(best_hist, label="Best")
    ax[0].set_title("Objective vs iterasi " + judul)
    ax[0].set_xlabel("Iterasi")
    ax[0].set_ylabel("Total ShippingFee")
    ax[0].legend()
    ax[1].scatter([p[0] for p in exp_hist], [p[1] for p in exp_hist], s=2)
    ax[1].set_title("e^(dE/T) terhadap iterasi " + judul)
    ax[1].set_xlabel("Iterasi")
    ax[1].set_ylabel("e^(dE/T)")
    fig.tight_layout()
    plt.show()