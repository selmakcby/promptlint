# Developer Promptları — Kötü vs İyi

Promptlint'in skor sistemi gerçek senaryolarla.

---

## 1. Refactor

**❌ Kötü** — Skor: 2/10
```
kodumu temizle, daha modern olsun
```
**Sorunlar:** belirsiz fiil, dosya yok, kapsam yok, format yok.

**✅ İyi** — Skor: 9/10
```
src/auth/login.ts dosyasındaki validatePassword fonksiyonunu manuel
regex yerine zod schema kullanacak şekilde refactor et. Test dosyalarına
dokunma. Sadece değişen kısımları diff olarak göster.
```

**Token farkı:** ~$5.00 vs ~$0.05 → **100× ucuz**.

---

## 2. Bug fix

**❌ Kötü** — Skor: 1/10
```
hata var çöz
```

**✅ İyi** — Skor: 9/10
```
TypeError: Cannot read property 'map' of undefined hatası
src/components/UserList.tsx:42'de oluşuyor.

Reproduce: kullanıcı listesi boşken sayfayı render et.
Beklenen: empty state mesajı göster.
Mevcut: crash.

Sadece UserList.tsx'i düzelt, parent component'lara dokunma.
```

---

## 3. Yeni özellik

**❌ Kötü** — Skor: 3/10
```
loading state ekle
```

**✅ İyi** — Skor: 9/10
```
src/pages/dashboard.tsx'te ProjectList component'ine loading state ekle.
- shadcn/ui Skeleton component'ini kullan
- Suspense ile sarmala
- Loading sırasında 6 skeleton row göster (placeholder yükseklik 64px)
- Error state'i için existing ErrorBoundary'i kullan, yeni component yazma
```

---

## 4. Test yazma

**❌ Kötü** — Skor: 2/10
```
test yaz
```

**✅ İyi** — Skor: 9/10
```
src/lib/auth.ts içindeki signIn fonksiyonu için Vitest test dosyası yaz.

Test edilmesi gerekenler:
1. Doğru credentials → user object döner
2. Yanlış password → AuthError fırlatır
3. Olmayan email → AuthError fırlatır
4. Network failure → retry mantığı çalışır (3 deneme)

Mock: supabase client'ı vi.mock ile mock'la.
Coverage hedefi: %100 line coverage.
Output: src/lib/auth.test.ts dosyası tam halini ver.
```

---

## Formül

```
İyi prompt = DOSYA + AKSIYON + KAPSAM + ÇIKTI

DOSYA   : tam yol veya dosya:satır
AKSIYON : net fiil + spesifik hedef
KAPSAM  : "DOKUNMA: x, y" — sınırları çiz
ÇIKTI   : format + uzunluk (diff/full/bullet)
```

Bu 4 alan dolduğunda skor 8+.
