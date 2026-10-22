<div align="center">

# 🚢 Cargo Placement Optimizer

**Optimasi penempatan kendaraan di geladak kapal kargo dengan _local search_**

Steepest Ascent · Sideways Move · Simulated Annealing · Genetic Algorithm

Tugas Besar **IF3070 – Dasar Inteligensi Artifisial** · 2026

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Course](https://img.shields.io/badge/IF3070-Tugas%20Besar%202026-informational)

</div>

<!-- TODO: taruh screenshot/GIF di doc/img/ lalu aktifkan baris di bawah
![Demo](doc/img/demo.gif)
-->

---

## Daftar Isi

- [Tentang Proyek](#tentang-proyek)
- [Fitur](#fitur)
- [Algoritma](#algoritma)
- [Struktur Repositori](#struktur-repositori)
- [Instalasi](#instalasi)
- [Cara Menjalankan](#cara-menjalankan)
- [Format Input JSON](#format-input-json)
- [Output yang Dihasilkan](#output-yang-dihasilkan)
- [Validasi & Kasus Uji](#validasi--kasus-uji)
- [Catatan Teknis](#catatan-teknis)
- [Laporan](#laporan)
- [Anggota Kelompok](#anggota-kelompok)

---

## Tentang Proyek

Program ini menyelesaikan masalah **penempatan kendaraan di geladak kapal kargo**: dari sekumpulan kendaraan, pilih
dan tempatkan sebagian (atau semuanya) di geladak berbentuk grid 2D supaya **total `ShippingFee` maksimum**.

**Komponen masalah**

| Komponen | Keterangan |
|---|---|
| Kapal | Geladak `w × l` sel dan `max_capacity` (berat maksimum) |
| Kendaraan | `id`, ukuran `w × l`, `fee` (ShippingFee), `weight`, `eta` |
| Placement | Posisi pojok kiri-atas `(x, y)` + orientasi `Horizontal` / `Vertical`; kendaraan boleh berada **di luar** kapal |

**Constraint** (harus selalu terpenuhi)

1. Kendaraan **tidak saling menumpuk**.
2. Kendaraan **tidak keluar dari geladak**.
3. Total berat kendaraan di dalam kapal **tidak melebihi** `max_capacity`.

**Fungsi objektif:** memaksimalkan jumlah `fee` kendaraan yang berada di dalam kapal.

> Koordinat memakai konvensi matriks: **baris = `x`** (lebar kapal), **kolom = `y`** (panjang kapal).
> Orientasi `Horizontal` berarti dimensi `(w, l)`, sedangkan `Vertical` berarti `(l, w)`.

---

## Fitur

- **4 algoritma** local search dalam satu antarmuka: Steepest Ascent, Sideways Move, Simulated Annealing, Genetic Algorithm.
- **Instance fleksibel:** kendaraan _random_ (dari seed) atau _manual_; state awal _random_ atau _manual_ (placement manual dicek validitasnya dan diminta ulang bila tidak valid).
- **3 mode output CLI:** `DEBUG`, `SUMMARY`, `QUICK`.
- **Tampilan terminal berwarna:** banner, tabel, matriks geladak berwarna per kendaraan, bar utilisasi, sparkline riwayat, dan spinner.
- **Validasi otomatis** pada setiap hasil (tidak numpuk, tidak keluar geladak, tidak overweight, value & berat konsisten, kurva terbaik tidak turun).
- **Mode bandingkan:** jalankan semua algoritma di instance yang sama dengan banyak seed, hasilnya berupa tabel, uji statistik, dan grafik.
- **Visualisasi:** PNG (layout geladak, riwayat pencarian, snapshot), GIF animasi, dan grafik analisis kualitas laporan.
- **Reproducible:** semua keacakan dikendalikan lewat `seed`.

---

## Algoritma

Seluruh algoritma memakai representasi dan _neighborhood_ yang sama (`src/define.py`), sehingga hasilnya bisa dibandingkan langsung.

### Representasi & Neighborhood

`State` menyimpan `Placement(x, y, orientation)` tiap kendaraan, peta okupansi sel, total berat, dan total fee. Evaluasi tetangga
dihitung secara **delta** (tanpa membangun state baru): hasilnya adalah total fee baru, atau `None` bila tetangga melanggar constraint.

| Move | Deskripsi |
|---|---|
| **Swap** | Dua kendaraan saling bertukar posisi (orientasi tetap milik masing-masing); salah satunya boleh berada di luar kapal |
| **Move** | Memindahkan kendaraan ke koordinat lain, mengeluarkannya dari kapal, atau memasukkannya ke kapal |
| **Rotate** | Mengubah orientasi kendaraan non-persegi (termasuk orientasi default kendaraan yang berada di luar kapal) |

Hill Climbing **mengenumerasi seluruh** tetangga feasible, sedangkan SA dan GA **mengambil tetangga/mutasi secara acak** dari ketiga jenis move di atas.

### Ringkasan Algoritma

| Algoritma | Berkas | Ide singkat |
|---|---|---|
| **Steepest Ascent** | `hill_climbing.py` | Evaluasi semua tetangga feasible, ambil yang terbaik (seri dipilih acak); berhenti saat tidak ada tetangga yang lebih baik |
| **Sideways Move** | `hill_climbing.py` | Seperti Steepest Ascent, tetapi boleh melangkah ke tetangga bernilai **sama** sampai `max_sideways` langkah berturut-turut (hitungan di-reset setiap ada peningkatan) |
| **Simulated Annealing** | `simulated_annealing.py` | Tetangga acak (Rotate/Move/Swap); move dengan `Δ ≥ 0` selalu diterima, move lebih buruk diterima dengan peluang `e^(Δ/T)`; suhu turun geometris `T ← T · r` sampai `T ≤ T_stop`; state terbaik sepanjang pencarian disimpan, dan kejadian _stuck_ di local optimum dicatat |
| **Genetic Algorithm** | `genetic_algorithm.py` | Populasi state valid; seleksi turnamen; _crossover_ memotong geladak dengan satu garis (kendaraan utuh di sisi kiri dari induk A, di sisi kanan dari induk B, sisanya diisi greedy berdasarkan fee) sehingga anak selalu valid; mutasi Swap/Move/Rotate; _elitism_; state terbaik sepanjang pencarian disimpan |

<details>
<summary><b>Parameter & nilai default</b></summary>

**Hill Climbing**

| Parameter | Default | Keterangan |
|---|---|---|
| `max_iters` | `10000` | Batas iterasi |
| `max_sideways` | `100` | Batas langkah sideways berturut-turut (khusus Sideways Move) |

**Simulated Annealing**

| Parameter | Default | Keterangan |
|---|---|---|
| `init_temp` | `50.0` | Suhu awal |
| `cooling_rate` | `0.999` | Faktor pendinginan, `0 < r < 1` |
| `stopping_temp` | `0.01` | Berhenti saat suhu ≤ nilai ini |
| `stuck_window` | `50` | Iterasi tanpa perubahan sebelum dicek apakah state berada di local optimum |

**Genetic Algorithm**

| Parameter | Default | Keterangan |
|---|---|---|
| `population_size` | `50` | Ukuran populasi |
| `generations` | `300` | Jumlah generasi |
| `crossover_rate` | `0.9` | Peluang dua induk di-crossover |
| `mutation_rate` | `0.9` | Peluang anak dimutasi |
| `mutation_steps` | `6` | Maksimum mutasi per anak |
| `elite_size` | `2` | Jumlah individu terbaik yang langsung lolos |
| `tournament_k` | `2` | Ukuran turnamen seleksi |
| `init_attempts` | `40` | Percobaan menaruh tiap kendaraan saat membuat state awal |

Proporsi jenis mutasi GA (efektif): Swap ≈ 27%, Move ≈ 53%, Rotate ≈ 20%.

</details>

> Penjelasan lengkap, analisis, dan perbandingan hasil ada di [laporan](#laporan).

---

## Struktur Repositori

```text
IF3070_G24_3D/
├── README.md
├── src/
│   ├── main.py                  # CLI utama (menu semua algoritma + mode bandingkan)
│   ├── ui.py                    # tampilan terminal: banner, tabel, matriks geladak, bar, sparkline, spinner
│   ├── define.py                # Problem, State, Placement, neighborhood, generator instance
│   ├── hill_climbing.py         # Steepest Ascent & Sideways Move
│   ├── simulated_annealing.py   # Simulated Annealing
│   ├── genetic_algorithm.py     # Genetic Algorithm
│   ├── experiment.py            # runner eksperimen: banyak seed, sweep parameter, statistik
│   └── visualizer.py            # grafik & visualisasi (matplotlib)
└── doc/                         # laporan (akan ditambahkan)
```

---

## Instalasi

**Prasyarat:** Python **3.10+**.

Inti program (algoritma + CLI) hanya memakai _standard library_. Library tambahan hanya dibutuhkan untuk visualisasi, mode bandingkan, dan `experiment.py`.

```bash
# 1. clone repositori
git clone https://github.com/Derren-Christopher/IF3070_G24_3D.git
cd IF3070_G24_3D

# 2. (opsional tapi disarankan) buat virtual environment
python -m venv .venv
# Windows:       .venv\Scripts\activate
# Linux / macOS: source .venv/bin/activate

# 3. pasang dependensi tambahan (visualisasi, mode bandingkan, experiment.py)
pip install matplotlib

# opsional: uji Mann-Whitney di stats.txt
pip install scipy
```

| Kebutuhan | Paket |
|---|---|
| Algoritma + CLI dasar | _(tidak ada)_ |
| Visualisasi PNG/GIF, mode bandingkan, `experiment.py` | `matplotlib` |
| Uji Mann-Whitney di `stats.txt` _(opsional)_ | `scipy` |

> **Terminal:** gunakan terminal modern (Windows Terminal, terminal VS Code, atau terminal Linux/macOS) dengan font monospace yang mendukung
> karakter _box-drawing_. Warna dimatikan otomatis jika output di-pipe atau variabel `NO_COLOR` diset, dan dipaksa menyala dengan `FORCE_COLOR=1`.

---

## Cara Menjalankan

### 1. CLI

```bash
python src/main.py
```

Alur interaktifnya:

1. Pilih **mode output** → pilih **algoritma** (1–4, atau 5 untuk _bandingkan semua_).
2. Isi **problem**: jumlah kendaraan, ukuran kapal, kapasitas, seed, dan sumber kendaraan (random/manual).
3. Untuk Hill Climbing & SA: pilih **state awal** (random/manual). Untuk semua algoritma: atur **parameter** (tekan `Enter` untuk default).
4. (Opsional) simpan visualisasi PNG dan GIF.
5. Hasil ditampilkan beserta validasi otomatis.

Semua mode selalu menampilkan **tabel penempatan state akhir, ringkasan, dan validasi otomatis**. Perbedaannya:

| Mode | Tambahan di luar tampilan dasar |
|---|---|
| `1` DEBUG | Matriks geladak awal & akhir **+** history algoritma (sparkline, sampel nilai, log `e^(Δ/T)` untuk SA) |
| `2` SUMMARY | Matriks geladak awal & akhir |
| `3` QUICK | _(tidak ada)_ |

> Matriks geladak digambar dengan lebar sel 4 (atau 3) karakter per kolom, jadi untuk geladak dengan banyak kolom pakai mode `QUICK`
> atau lebarkan jendela terminal agar tampilan tidak terpotong.
>
> Folder `output/` (visualisasi satu run) dan `hasil/` (mode bandingkan) dibuat relatif terhadap direktori tempat perintah dijalankan.

### 2. Mode Bandingkan (menu `5`)

Menjalankan keempat algoritma di **instance dan seed yang sama** (seed `0 … N-1`), lalu menyimpan CSV, tabel ringkasan,
uji statistik, dan grafik. Tersedia suite tambahan: `ga` (sensitivitas parameter GA), `sideways` (batas sideways),
`scale` (jumlah kendaraan), `capacity` (rasio kapasitas), dan `trace` (snapshot + GIF). Tekan `Enter` pada prompt suite untuk memakai `trace`.

### 3. Runner Eksperimen (non-interaktif)

```bash
python src/experiment.py --quick                       # cek cepat semua berjalan
python src/experiment.py                               # 25 kendaraan, kapal 10x20, 10 seed
python src/experiment.py --suites all --pdf            # semua analisis + PDF vektor
python src/experiment.py --runs 20 --n-vehicles 30 --ship-w 12 --ship-l 24
```

<details>
<summary><b>Daftar opsi</b></summary>

| Opsi | Default | Keterangan |
|---|---|---|
| `--suites` | `main,trace` | `main`, `ga`, `sideways`, `scale`, `capacity`, `trace`, atau `all` |
| `--n-vehicles` | `25` | Jumlah kendaraan |
| `--ship-w` / `--ship-l` | `10` / `20` | Ukuran geladak |
| `--capacity` | 60% total berat | Kapasitas berat |
| `--problem-seed` | `1` | Seed pembuat instance (sama untuk semua algoritma) |
| `--runs` | `10` | Jumlah seed per algoritma |
| `--sweep-runs` | `5` | Jumlah seed per konfigurasi di suite sweep/scale/capacity |
| `--max-sideways` | `100` | Batas sideways |
| `--sa-temp` / `--sa-cooling` / `--sa-stop` | `50` / `0.999` / `0.01` | Parameter SA |
| `--population` / `--generations` | `50` / `300` | Parameter GA |
| `--quick` | – | Preset kecil dan cepat |
| `--pdf` | – | Simpan juga PDF vektor |
| `--out` | `hasil` | Folder output |

</details>

---

## Format Input JSON

Fungsi `define.load_problem(path)` dapat memuat instance dari berkas JSON. Fungsi ini tersedia **secara programatik**
(`from define import load_problem`) dan belum dipanggil dari menu CLI.

```json
{
  "Ship": { "w": 10, "l": 20, "max_capacity": 100 },
  "Vehicles": [
    { "id": "V01", "w": 2, "l": 4, "fee": 40, "weight": 8, "eta": 0 },
    { "id": "V02", "w": 3, "l": 3, "fee": 55, "weight": 12 }
  ]
}
```

`eta` bersifat opsional (default `0`).

---

## Output yang Dihasilkan

<details>
<summary><b>Satu run dari CLI (folder <code>output/</code>, bila visualisasi dipilih)</b></summary>

| Berkas | Isi |
|---|---|
| `state_<algoritma>_seed<N>.png` | Detail state akhir: geladak, fee per kendaraan, utilisasi |
| `run_<algoritma>_seed<N>.png` | Layout awal, layout akhir, dan kurva riwayat |
| `sa_<algoritma>_seed<N>.png` | Analisis khusus SA (hanya untuk Simulated Annealing) |
| `snapshots_<algoritma>_seed<N>.png` | Snapshot perkembangan layout selama pencarian |
| `anim_<algoritma>_seed<N>.gif` | Animasi perkembangan layout (bila GIF dipilih) |

</details>

<details>
<summary><b>Mode bandingkan / <code>experiment.py</code> (folder <code>hasil/</code>)</b></summary>

| Berkas | Isi |
|---|---|
| `results.csv` | Hasil tiap run (algoritma, seed, value awal/akhir, gap, durasi, validitas) |
| `summary.txt`, `stats.txt` | Tabel ringkasan; CI 95% bootstrap, CV, Cohen's d, uji Mann-Whitney |
| `01_instance.png` | Gambaran instance (katalog kendaraan, fee, ringkasan kapal) |
| `02_convergence.png` | Kurva konvergensi rata-rata antar seed |
| `03_distribution.png` | Distribusi value akhir dan durasi |
| `04_gap.png`, `05_improvement.png` | Gap ke batas atas; peningkatan dari state awal |
| `06_time_vs_value.png`, `07_ranking.png` | Trade-off kualitas vs waktu; frekuensi peringkat |
| `08_hc_stats.png`, `08b_sa_stats.png` | Statistik khusus Hill Climbing dan Simulated Annealing |
| `09_best_layouts.png`, `10_detail_*.png`, `11_run_*.png` | Layout terbaik dan detail per algoritma |
| `20_…` – `24_…` | Suite tambahan (sweep GA, heatmap, sideways, skalabilitas, kapasitas) |
| `30_snapshots_*.png`, `31_anim_*.gif` | Snapshot dan animasi perkembangan layout |
| `DAFTAR_GAMBAR.md` | Daftar gambar beserta usulan caption untuk laporan |

</details>

---

## Validasi & Kasus Uji

Setiap hasil dicek ulang secara independen dari kode algoritma:

- ✔ State akhir valid (tidak numpuk / keluar geladak / overweight)
- ✔ Value = jumlah fee kendaraan di dalam; berat = jumlah berat kendaraan di dalam
- ✔ Kurva terbaik tidak pernah turun, dan ujungnya sama dengan value akhir
- ✔ Value akhir ≥ value awal

**Kasus manual untuk cross-check** (pilih sumber kendaraan `M`; nilai optimum dihitung dengan brute force):

| Kasus | Setup | Optimum | Pengamatan (10 seed, state awal random) |
|---|---|---|---|
| Kapasitas membatasi | Kapal lebar `5` panjang `5`, cap `10`. V1 `2×2` fee 100 berat 10; V2 `2×2` fee 60 berat 5; V3 `2×2` fee 55 berat 5 | **115** (V2 + V3) | Steepest & Sideways kadang berhenti di **100** (local optimum); SA & GA selalu 115 |
| Rotasi wajib | Kapal lebar `2` panjang `4`, cap besar. V1 lebar `4` panjang `2` fee 10; V2 `1×1` fee 3 | **10** (V1 dirotasi memenuhi geladak, V2 di luar) | Steepest kadang berhenti di **3**; algoritma lain selalu 10 |
| Terlalu besar | Kapal `3×3`, cap besar. V1 `5×5` fee 1000; V2 `1×1` fee 1 | **1** | V1 tidak pernah masuk di semua algoritma |
| Kapasitas kecil | Kapal `3×3`, cap `1`, dua kendaraan `1×1` berat 5 | **0** | Semua kendaraan di luar |

Dua kasus pertama berguna untuk laporan sebagai contoh nyata **local optimum** pada Hill Climbing.

**Cek cepat dengan instance random** (12 kendaraan, kapal `8×12`, kapasitas `79`, seed `0`, state awal random):

| Algoritma | Parameter | Value awal → akhir |
|---|---|---|
| Steepest Ascent | default | 327 → 368 |
| Sideways Move | `max_sideways = 30` | 327 → 488 |
| Simulated Annealing | `T=50`, `r=0.99`, `T_stop=0.01`, `window=30` | 327 → 446 |

> Angka di atas bergantung pada versi `define.py` dan urutan penggunaan RNG. Bila hasil berbeda, periksa dulu apakah kode di repo sudah sama.

---

## Catatan Teknis

- **`eta`** disimpan pada data kendaraan tetapi **belum dipakai** pada constraint maupun fungsi objektif.
- **Batas atas value** (dipakai untuk menghitung _gap_) berasal dari relaksasi _fractional knapsack_ terhadap berat dan luas geladak.
  Ini **bukan nilai optimum**, jadi gunakan istilah "gap ke batas atas".
- **Sumbu iterasi tidak sebanding** antar algoritma: satu iterasi Hill Climbing memindai seluruh tetangga, satu iterasi SA hanya satu proposal,
  dan satu generasi GA memproses seluruh populasi. Untuk perbandingan yang adil, gunakan durasi atau jumlah evaluasi.
- **Plateau pada Sideways Move:** operasi Rotate pada kendaraan yang berada di luar kapal selalu feasible dan tidak mengubah value,
  sehingga plateau hampir selalu tersedia selama masih ada kendaraan non-persegi di luar kapal.
- **Move netral pada SA:** karena move dengan `Δ = 0` selalu diterima, sebagian besar move yang diterima SA bersifat netral, bukan move yang lebih buruk.
- Mutasi Swap membutuhkan minimal **2 kendaraan**, sehingga GA mensyaratkan jumlah kendaraan ≥ 2.

---

## Laporan

> 📄 Laporan mengenai algoritma, eksperimen, dan analisis hasil akan ditambahkan di folder [`doc/`](doc/).

<!-- TODO: setelah laporan ada, ganti kalimat di atas dengan tautan ke berkas, mis. [Laporan Tugas Besar](doc/Laporan.pdf) -->

---

## Anggota Kelompok

**Kelompok 3D · IF3070 Dasar Inteligensi Artifisial**

| Nama | NIM | Kontribusi |
|---|---|---|
| M.B. Adyanti Narandita | 18224040 | Simulated Annealing, pengerjaan laporan, visualisasi |
| Derren Christopher Boenardi | 18224040 | Define environment, Hill Climbing, integrasi kode |
| Rafeyfa Dea Putri Ramadhani | 18224044 | Genetic Algorithm, pengerjaan laporan, run experiment |

---

<div align="center">

Tugas Besar IF3070 Dasar Inteligensi Artifisial · 2026

</div>
