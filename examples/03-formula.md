# Prompt Formülü

Promptlint'in skoru aşağıdaki 5 boyutu ölçer. Her boyutta puan toplarsın.

---

## 1. UZUNLUK / DETAY

| Karakter | Etki | Sebep |
|----------|------|-------|
| < 15     | -5   | Bağlam yok, model tahmin etmek zorunda |
| 15-40    | -2   | Yetersiz, takip soruları olacak |
| 40-100   | OK   | Yeterli alan |
| 100+     | +    | Detaylı, single-shot biter |

---

## 2. SPESİFİKLİK

Belirsiz fiil **kötü**: `düzelt`, `temizle`, `iyileştir`, `biraz`, `güzel olsun`, `daha iyi yap`.

Spesifik fiil **iyi**: `refactor et X pattern ile`, `Y'yi Z'ye çevir`, `şu hatayı X'e göre düzelt`.

---

## 3. REFERANS

Promptun bir **somut hedef** içermeli:
- Dosya yolu: `src/auth/login.ts`
- Fonksiyon: `validatePassword()`
- Satır: `:42-78`
- Component: `<UserList>`
- Hata mesajı: `"TypeError: ..."`

Referans yoksa model tüm kod tabanını tarar → büyük cache write → pahalı.

---

## 4. KAPSAM

İyi prompt **ne yapmasın**ı da söyler:
- `Test dosyalarına dokunma`
- `Sadece bu component'i değiştir, parent'a dokunma`
- `regex yerine zod kullan, ama validation logic'i koru`

Kapsam yoksa model "yardımcı olmak için" ekstra dosyalara dokunur → diff şişer → output token patlar.

---

## 5. ÇIKTI FORMATI

Hangi format/uzunlukta cevap istediğin belli olmalı:
- `Tablo şeklinde`
- `3 madde, her biri tek cümle`
- `Sadece değişen satırları diff olarak göster`
- `Tam dosya halini ver`
- `250 kelimeden uzun olmasın`

Format yoksa model "kapsamlı" cevap yazar → output token patlar.

---

## Skor → ne yapar

```
9-10  : silent pass — promptlint sessizdir
7-8   : silent pass — yeterince iyi
4-6   : pass + Claude'a coach notu (sana sormadan netleştirir)
0-3   : BLOK — kullanıcıya geri döndürür, yeniden yazdırır
```

---

## Master template

```
[DOSYA / KAPSAM]
src/components/Pricing.tsx

[AKSIYON]
3 fiyat planı için card'lar ekle. shadcn/ui Card kullan.
Plans: Free / Pro ($9/ay) / Enterprise (özel).

[SINIRLAR]
Sadece bu dosyayı değiştir. Existing import'lara dokunma.
Mevcut Pricing component'ini koru, sadece yeni section ekle.

[ÇIKTI]
Tam dosya halini ver. Türkçe yorumla.
```

Her promptu bu 4 başlığa göre yazarsan: skor ortalama 9/10.
