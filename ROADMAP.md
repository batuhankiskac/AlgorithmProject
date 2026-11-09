# Yol Haritası — CMP 3005 Term Project

Son teslim: **13 Aralık 2026 Pazar, 23:59** (Teams). Bugün: 9 Kasım 2026, kalan süre ~5 hafta.

## Temel kararlar

| Karar | Seçim | Neden |
|---|---|---|
| Dil | Python 3 + numpy (gerekirse numba) | Hızlı geliştirme, plot/istatistik kolay; TS iç döngüsü O(1) delta ile yeterince hızlı |
| Mesafe | Önceden hesaplanmış n×n matris | Tüm algoritmalar O(1) erişim; CVRPLIB için tam sayıya yuvarlanmış |
| Filo limiti K | Split'te **sınırlı filo** varyantı, TS'de rota sayısı kontrolü, CW sonrası onarım | CW ve klasik Split K'yı kendiliğinden aşabilir |
| Kapasite (TS) | Cezalı arama: λ·(aşım), λ adaptif | Uygunsuz bölgeden geçiş aramayı çeşitlendirir |
| Rapor | LaTeX (Overleaf) veya Markdown→PDF | 10–16 sayfa + ekler, İngilizce |
| Tekrarlanabilirlik | Her koşu: instance, algoritma, seed, süre, maliyet → `results/*.csv` | Rubrikte zorunlu |

## Bağımlılık grafiği (kritik yol)

```
            ┌────────────── Teori (T1) ───────────────┐  (bağımsız, paralel)
            │                                          ▼
Çekirdek ──►├─► Clarke–Wright ──► Tabu Search ──┐    Rapor ──► Slayt ──► Teslim
(parser,    │                                   ├─► Deneyler ─┘
 evaluator, ├─► Split DP ──────► GA ────────────┘      ▲
 checker)   │                                          │
            └─► Tiny exact + MediDrone üretici ────────┘
```

**Kritik yol:** Çekirdek → (CW, Split) → (TS, GA) → tuning → deneyler → rapor.
Çekirdek modül ilk hafta bitmezse her şey kayar; o yüzden ilk iş o.

## İş akışları ve sahiplik (3–4 kişi)

Paralel çalışılabilmesi için her akışın kendi dosyaları var; ortak dosya yalnızca `src/cvrp/instance.py` ve `solution.py` (çekirdek sahibi yönetir).

| Akış | Sahip | Dosyalar | İçerik |
|---|---|---|---|
| **A – Çekirdek & Veri** | Üye 1 | `instance.py`, `generator.py`, `solution.py`, `checker.py`, `exact.py` | CVRPLIB parser, MediDrone üretici, mesafe matrisi, maliyet, bağımsız checker, tiny instance'lar için DP/brute force |
| **B – GA** | Üye 2 | `split.py`, `ga.py` | Split DP (sınırlı filo), OX, mutasyon, turnuva, elitizm, duplicate reddi; opsiyonel memetik 2-opt |
| **C – CW & TS** | Üye 3 | `clarke_wright.py`, `tabu.py`, `moves.py` | CW savings + K onarımı, relocate/swap/2-opt/2-opt*, delta formülleri, tabu listesi, aspirasyon, adaptif λ |
| **D – Teori & Deneyler** | Üye 4 (3 kişiyse A ile paylaşılır) | `report/`, `experiments/` | Task 1 ispatları, deney koşucusu, plotlar, istatistik testi |

Ortak arayüz (ilk gün sabitlenecek, sonra değişmeyecek):

```python
inst = Instance(n, Q, K, demand: np.ndarray, D: np.ndarray, coords, side)
sol  = list[list[int]]           # rotalar, depo (0) hariç
cost(inst, sol) -> float
check(inst, sol) -> (ok: bool, reasons: list[str])
solve(inst, time_limit: float, seed: int) -> (sol, cost, history[(t, best)])
```

## Zaman çizelgesi

### Hafta 1 · 9–15 Kasım — Temel
- [ ] Ekip seed hesabı (öğrenci numaralarının son 4 hanesi) — yorumu netleştir, rapora yaz
- [ ] Ortak arayüzü sabitle (yukarıdaki imzalar)
- [ ] A: CVRPLIB parser + 4 instance + BKS tablosu (`data/cvrplib/bks.csv`)
- [ ] A: Mesafe matrisi (CVRPLIB için yuvarlama), `cost`, `check` + testler
- [ ] A: MediDrone üretici (1000×1000, 4–6 küme + %20 rastgele, Q=100, K=⌈Σq/Q⌉+1, P=150)
- [ ] A: Tiny instance'lar (n=7,8,9) + kesin optimum (Held–Karp tarzı subset DP veya ILP)
- [ ] D: Task 1 taslakları — NP üyeliği, HC→TSP (1/2 ağırlık, metrik kalır), TSP→CVRP (K=1, qᵢ=1, Q=n), Bin Packing → uygunluk, Boğaz metrik ispatı
- [ ] B/C: Okuma — Prins 2004 (Split), Clarke–Wright 1964, Glover & Laguna

### Hafta 2 · 16–22 Kasım — Baseline + M1
- [ ] C: Clarke–Wright (O(n² log n)) + K aşımı için onarım
- [ ] B: Split DP (DAG, rekürans, O(n·L) / sınırlı filo O(K·n·L)) + tiny'de doğrulama
- [ ] B: GA iskeleti (temsil, OX, mutasyon, turnuva)
- [ ] C: TS hamleleri + delta formülleri, her delta'yı tam yeniden hesaplamaya karşı test et
- [ ] D: MediDrone instance plotu (Boğaz çizgisi)
- [ ] **20 Kasım Cuma — M1 teslim** (2–3 sayfa: tanımlar, indirgeme taslakları, seed, instance plotu)

### Hafta 3 · 23–29 Kasım — Metasezgiseller
- [ ] B: GA tamamla — elitizm, duplicate reddi, zaman limiti, convergence history
- [ ] C: TS tamamla — tabu listesi/tenure, aspirasyon, adaptif λ, candidate list
- [ ] D: Deney koşucusu (`experiments/run.py`): instance × algo × seed → CSV
- [ ] Hepsi: Tiny instance'larda optimuma ulaşılıyor mu? Bulunan her hata için test ekle
- [ ] İlk kaba tuning A-n32-k5'te

### Hafta 4 · 30 Kasım–6 Aralık — Tuning, analiz, M2
- [ ] **4 Aralık Cuma — M2 demo** (CW + en az bir metasezgisel, A-n32-k5)
- [ ] B/C: Parametre çalışması (ör. tenure–gap, mutasyon oranı–çeşitlilik)
- [ ] D: Task 6 — iterasyon başına teorik maliyet; ölçüm için ek boyutlar (n = 50…400) üret, log–log eğim
- [ ] D: Delta vs. tam değerlendirme süre karşılaştırması
- [ ] Opsiyonel bonus: memetik GA

### Hafta 5 · 7–13 Aralık — Koşular, rapor, slayt
- [ ] Tam deney: 10 seed × {GA, TS} × 6 instance, eşit bütçe (30 s n≤50, 60 s üstü) ≈ 80 dk + CW + tiny
- [ ] Tablolar (best/mean/std/gap/runtime), convergence eğrileri, MediDrone rota görseli, Boğaz geçiş sayısı
- [ ] Bonus: Wilcoxon signed-rank (GA vs TS)
- [ ] Rapor bölümleri (paralel yazım, bölüm sahipleri = akış sahipleri), Ek A katkı tablosu
- [ ] README'ye her tablo/figür için komut
- [ ] Slaytlar (10–15 dk)
- [ ] **13 Aralık 23:59 — Teslim**: PDF + repo linki + CSV + slaytlar
- [ ] Sözlü savunma provası: herkes her bölümü anlatabilmeli

## Riskler

| Risk | Önlem |
|---|---|
| CW / Split K'dan fazla rota üretir | Sınırlı filo Split, CW sonrası birleştirme/onarım, checker K'yı da kontrol eder |
| Yuvarlama hatası → yanlış gap | Parser testi: bilinen BKS çözümünü yükle, maliyeti BKS ile karşılaştır |
| Delta formülünde hata | Her hamle için rastgele testte delta == tam maliyet farkı |
| Python TS'de yavaş | Önce profil; gerekirse numba veya candidate list (granular neighborhood) |
| Seed çakışması / yorum belirsizliği | Hesabı açıkça rapora yaz; gerekirse hocaya sor |
| Son hafta yığılması | Deney koşucusu 3. haftada hazır olsun; deneyler arka planda koşarken rapor yazılır |
| Sözlü savunmada bireysel soru | Haftalık 15 dk "birbirine anlat" turu |

## Tanım: "bitti"

Bir modül, testleri geçtiğinde, checker'dan geçen çözüm ürettiğinde ve README'de çalıştırma komutu olduğunda bitmiş sayılır.
