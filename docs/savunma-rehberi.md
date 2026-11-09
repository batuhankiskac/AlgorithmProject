# Sözlü savunma rehberi

Sorular üyelere tek tek soruluyor ve herkes her bölümü anlatabilmeli. Her soruda önce kısa cevabı verin, sonra "neden"ini açıklayın. Ayrıntılar `report/report.pdf`, `docs/notes_ga.md` ve `docs/notes_ts.md` içinde.

## 1. Problem ve teori

**CVRP nedir?** Bir depo, talepleri qᵢ olan n müşteri, kapasitesi Q olan en fazla K araç var. Her müşteri tam bir kez ziyaret edilir, her rota depoda başlayıp depoda biter ve rota yükü Q'yu aşamaz. Amaç toplam mesafeyi en aza indirmek.

**Karar versiyonu neden NP'de?** Sertifika rotaların listesi. Doğrulayıcı her müşterinin bir kez geçtiğini, yüklerin ≤ Q olduğunu, rota sayısının ≤ K olduğunu ve toplam maliyetin ≤ B olduğunu O(n) sürede kontrol eder.

**HC ≤p TSP nasıl kuruluyor?** Grafta kenar olan çiftlere ağırlık 1, olmayanlara 2 verilir ve B = |V| alınır. Maliyeti ≤ |V| olan bir tur yalnızca 1 ağırlıklı kenarları kullanabilir; bu da tam olarak bir Hamilton çevrimidir. 1/2 ağırlıkları üçgen eşitsizliğini sağlar. Bu önemli, çünkü bizim CVRP tanımımız metrik mesafe istiyor.

**TSP ≤p CVRP?** Bir şehir depo yapılır; diğerleri qᵢ = 1 olan müşteriler olur, Q = n ve K = 1 alınır. Tek bir rota, tam olarak bir TSP turudur.

**İki indirgemenin bileşimi neden polinom?** İlk indirgemenin çıktısı polinom büyüklükte. İkinci indirgeme bu çıktı üzerinde polinom sürede çalışır ve polinomun polinomu yine polinomdur.

**"Gizli" ikinci NP-zor problem?** "Müşteriler K araca sığar mı?" sorusu Bin Packing'in ta kendisi ve güçlü anlamda NP-tam. Bu yüzden uygun bir çözüm bulmak bile zor olabilir. Somut örnek: Clarke–Wright, A-n45-k6'da K = 6 yerine 7 rota üretiyor. Bu yüzden iki metasezgisel de kapasite aşımına ceza ile izin veriyor.

**Boğaz cezası metriği bozar mı?** Bozmaz. i ile k aynı taraftaysa sol tarafta ceza yoktur. Farklı taraflardaysa j hangi tarafta olursa olsun i→j→k yolunun tam bir ayağı Boğaz'ı geçer, dolayısıyla sağ tarafta da bir P vardır. Daha kısa ispat: [taraf(i) ≠ taraf(j)] bir kesim metriğidir ve iki metriğin toplamı yine metriktir.

**Yaklaşım algoritmaları (bonus)?** Iterated tour partitioning (ITP) bir TSP turunu kapasiteye uygun parçalara böler. Bölünemez taleplerde garanti yaklaşık 2 + α'dır; Christofides algoritmasıyla (α = 1,5) ≈ 3,5. Kullandığımız alt sınırlar TSP* ve radyal sınır (2/Q)·Σ qᵢ·d(0,i).

## 2. Algoritmalar

**Clarke–Wright:** tasarruf s(i,j) = d0i + d0j − dij. Tasarruflar büyükten küçüğe sıralanır ve rotalar birleştirilir. Karmaşıklık O(n² log n), baskın terim sıralama. Kapasiteye uyar ama K'yı gözetmez.

**Split nedir, neden O(nL)?** Düğümleri 0..n olan bir DAG düşünün. (i, j) yayı, T_{i+1}…T_j müşterilerinden oluşan tek bir rotayı temsil eder. En kısa 0→n yolu en iyi bölmedir. İç döngü yük Q'yu aştığı anda durur, bu yüzden her i için en fazla L adım atılır ve toplam O(nL) olur. Bizim verimizde L ≈ 6,5. K ile sınırlı versiyon katmanlı DP'dir ve O(KnL) sürer.

**GA neden yumuşak kapasite kullanıyor?** Doluluk oranı %98,8 olan A-n45-k6'da rastgele turların %0'ı K rotaya uygun şekilde bölünebiliyor. Bu yüzden rota başına 1,5Q'ya kadar yüke izin veriyor, aşımı λ ile cezalandırıyoruz. λ, çocukların yaklaşık %40'ı uygun olacak şekilde uyarlanıyor.

**GA operatörleri:**
- Seçim: ikili turnuva.
- Çaprazlama: OX. Ebeveyn 1'den ardışık müşteri dilimlerini, yani rota parçalarını korur.
- Mutasyon: segment ters çevirme. Turda yalnızca 2 komşuluğu değiştirir.
- Yerine koyma: (μ+λ), elitist.
- Kopya reddi: fitness farkı 0,5'ten küçükse aday reddedilir.
- Yeniden başlatma: 60 nesil iyileşme olmazsa.
- Memetik kısım: çocukların %50'sine yerel arama uygulanır.

**TS komşulukları:** relocate, swap, 2-opt, 2-opt*. Her hamlenin maliyet farkı O(1)'de hesaplanır. Örnek, relocate için:
Δ = d(a,u) + d(u,b) − d(a,b) − [d(p,u) + d(u,s) − d(p,s)]

**Tabu özelliği neden yay?** Silinen yay belli bir süre geri eklenemez; süre U[5,15]. Yay tanımı beş hamle türünün hepsinde aynı şekilde çalışır. "(müşteri, rota)" tanımı ise 2-opt* sonrasında belirsizleşir. Aspirasyon: tabu bir hamle, yeni en iyi uygun çözümü veriyorsa yapılabilir.

**Kapasite nasıl yönetiliyor?** Amaç fonksiyonu f = c + λ·aşım. Mevcut çözüm aşımlıysa λ×1,5, değilse λ/1,5 yapılır. Arama böylece uygunluk sınırının iki yanında salınır ve en iyi uygun çözüm döndürülür.

**Aday listesi:** her müşterinin 20 en yakın komşusu. Bir iterasyonun maliyetini Θ(n²)'den Θ(nk)'ya düşürür.

## 3. Karmaşıklık (Task 6)

- **TS iterasyonu:** Θ(nk) tarama + O(n) uygulama, sabit k için Θ(n). Ölçülen eğim 1,04.
- **GA nesli:** Split O(KnL) ve K ∝ n olduğu için ikinci dereceden büyür; yerel arama yaklaşık Θ(ng). Ölçülen eğim 1,51 ve n büyüdükçe 2'ye yaklaşıyor (n = 400–800 arasında yerel eğim 1,75).
- **Split:** eğim 1,05, çünkü L sabit.
- **Clarke–Wright:** eğim 2,20, yani n² log n.
- **Delta ve tam değerlendirme karşılaştırması:** delta değerlendirme n = 50'de 15 kat, n = 800'de 124 kat hızlı. Fark Θ(n) oranında büyüyor.

## 4. Deneyler

- **Protokol:** 10 seed; GA ve TS'ye eşit duvar saati bütçesi (n ≤ 50 için 30 s, üstü için 60 s, tiny instance'lar için 2 s). İkisi de Clarke–Wright çözümüyle başlıyor. Gap = 100·(maliyet − BKS)/BKS.
- **Sonuçlar:**
  - GA, 40 benchmark koşusunun 38'inde BKS'e ulaştı.
  - TS, A-n80-k10'da ortalama %0,25 gap'te kaldı.
  - Tiny instance'larda iki algoritma da 10 koşunun 10'unda optimumu buldu.
  - GA ile TS arasındaki fark anlamlı (Wilcoxon p ≈ 0,00025).
- **Neden GA daha iyi?** Çaprazlama rota parçalarını birleştiriyor, Split rotaların nereden kesileceğini yeniden optimize ediyor ve popülasyon varyansı azaltıyor. Yerel arama kapatılınca gap %4'e çıkıyor ve çeşitlilik çöküyor.
- **Boğaz:** P = 0 ve P = 150 aynı rota yapısını veriyor: 9 saf Avrupa, 6 saf Asya rotası. Depo boğazın üstünde olduğu için Avrupa'ya giden her rota tam iki kez geçiyor. Ceza fiilen Avrupa rotası başına sabit 300'e dönüşüyor ve toplam ceza ≥ 300·⌈875/100⌉ = 2700. Planlarımız bu alt sınıra ulaşıyor.
- **Parametreler:**
  - Tabu tenure'da U-eğrisi var: 3 çok kısa (döngüye giriyor), 30 ve üstü çok uzun; en iyisi 7–15 aralığı.
  - Mutasyon oranının etkisi küçük.
  - Yerel arama (memetik kısım) kritik.

## 5. Kod

- **Bağımsız checker:** maliyeti çözücülerin mesafe matrisini kullanmadan, doğrudan koordinatlardan yeniden hesaplar.
- **Parser doğrulaması:** yayımlanmış optimal çözümler tam olarak 784, 944, 1354 ve 1763 veriyor. CVRPLIB mesafeleri nint ile yuvarlanıyor.
- **Testler:** her delta formülü rastgele hamlelerde tam yeniden hesaplamayla karşılaştırılıyor; kesin DP brute force ile karşılaştırılıyor.
- **Tekrarlanabilirlik:** bütün rastgelelik seed'li `random.Random(seed)`'den geliyor.

## Muhtemel zor sorular

- **"Neden GA ile TS'yi aynı başlangıçla başlattınız?"** Adalet için. İkisi de aynı Clarke–Wright çözümünden başlıyor; fark yalnızca arama stratejisinden geliyor.
- **"MediDrone'da optimum olduğunu biliyor musunuz?"** Hayır. 10 bağımsız GA koşusu aynı maliyette buluştu; bu güçlü bir işaret ama ispat değil. Kesin DP bu boyutta çalışmaz.
- **"Yerel aramanın pas sayısı polinom mu?"** A priori sınır yok, her hamle yalnızca f'yi azaltmak zorunda. Deneysel olarak küçük bir sabit.
