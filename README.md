<p align="center">
  <img src="./assets/cover.svg" alt="promptlint — Claude Code için Türkçe prompt grader" width="100%"/>
</p>

<p align="center">
  <code>real-time prompt scoring</code> ·
  <code>auto token pop-up</code> ·
  <code>chat içi toggle</code> ·
  <code>Haiku LLM-judge (opt-in)</code> ·
  <code>Türkçe</code>
</p>

---

# promptlint

> **Claude Code için real-time prompt kalite kontrolü.** Default-off — kurulur ama hiçbir şey yapmaz. `:lint on` ile açarsın, demolaman bittikten sonra `:lint off` ile kapatırsın. Hayatına engel olmaz.

## ⚠️ v3 (default-off) → güvenli kurulum

Önceki v2'de kurulum yapan herkes filter sürekli açıktı, "ne yapsam" gibi meta-soruları bile bloke ediyordu. **v3'te bu düzeltildi**: kurulum sonrası filter **kapalı** durur, sen `:lint on` yazınca açılır. Token pop-up ayrı bir mekanizma — o açık kalır, faydalı.

---

## v2 ne getirdi

| Özellik | Ne yapar |
|---------|----------|
| **Hibrit grader** | Önce hızlı regex kuralları, sonra (opsiyonel) Haiku LLM-judge — `ANTHROPIC_API_KEY` varsa otomatik aktif, yoksa rules fallback |
| **Otomatik token pop-up** | Stop hook her Claude cevabından sonra ekrana token kutusu çizer (son turn + oturum + maliyet) |
| **Chat içi toggle** | `:lint off` / `:lint on` yazarak filtreyi anında aç/kapat — yeniden başlatma yok |
| **5 boyutlu rubric** | spesifiklik, aksiyon, sınır, format, bağlam — ValidMind Clarity standardı |

---

## Ne görürsün

### Kötü prompt → BLOK (skor 0-3)
```
> kodumu temizle

🚨 PROMPTLINT — Skor: 2/10  (📐 RULES)

Sorunlar:
  • Çok kısa — daha çok detay verebilirsin
  • Belirsiz fiil — hangi dosya? hangi pattern?
  • Spesifik referans yok — dosya, fonksiyon ekle

Önerilen format:
  → DOSYA / KAPSAM   (src/auth/login.ts:42-78)
  → AKSIYON          (validatePassword'ı zod schema ile refactor et)
  → SINIRLAR         (test dosyalarına dokunma)
  → ÇIKTI            (sadece değişen satırları göster)

İpucu: filtreyi kapatmak istersen :lint off yaz
```

### Orta prompt → COACH NOTE (skor 4-6)
```
> react useEffect ekle

🟡 PROMPTLINT — Skor: 4/10  (🤖 LLM)  ·  Claude netleştirici sorular soracak
   ↳ Spesifik referans yok; Format yok

[Claude bu turn doğrudan kod yazmaz, önce 3-4 soru sorar]
```

### İyi prompt → SESSİZ GEÇER (skor 7-10)
```
> src/auth/login.ts'deki validatePassword'ı zod ile refactor et. Test'lere dokunma.

[Hiçbir uyarı yok, Claude direkt işe girişir]
```

### Her cevaptan sonra → TOKEN POP-UP
```
┌─ 📊 PROMPTLINT · TOKEN ───────────────────────────────────────┐
│ son turn  · in     29  out  1.2k  cw   45k  cr  120k  $ 0.0234
│ oturum    · top  166k  (opus)                       $ 3.4804
└───────────────────────────────────────────────────────────────┘
```

### Chat içi kontrol — `:lint on/off/status`
```
> :lint on
🔔 promptlint AÇILDI. Kapatmak için: :lint off

> :lint off
🔕 promptlint kapatıldı (sessiz mod). Açmak için: :lint on

> :lint status
ℹ️  promptlint durumu: kapalı (varsayılan)
```

**Default davranış: KAPALI.** Kurulum yaptıktan sonra hook çalışır ama hiçbir prompt'u bloke etmez. Demo etmek için `:lint on`, sonra `:lint off`.

---

## Skor sistemi

| Skor | Davranış |
|------|----------|
| 7-10 | Silent pass — promptlint sessizdir |
| 4-6  | Pass + visible warning + Claude'a coach note |
| 0-3  | BLOK — kullanıcıya geri döner, yeniden yazdırır |

---

## Kurulum

```bash
git clone https://github.com/selmakcby/promptlint.git
cd promptlint
./install.sh
```

`install.sh`:
1. `prompt-checker.py` ve `token-reporter.py` hooklarını `~/.claude/hooks/` altına kopyalar
2. `prompt-coach` skill'ini `~/.claude/skills/` altına kopyalar
3. `token-counter.py` standalone CLI'yı `~/bin/` altına kopyalar
4. `anthropic` SDK var mı kontrol eder (yoksa rules fallback)
5. Sana `~/.claude/settings.json`'a eklenecek JSON'u verir

**Manuel adım** — `~/.claude/settings.json`'a iki hook ekle (root level `hooks` objesi içine):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/prompt-checker.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/token-reporter.py"
          }
        ]
      }
    ]
  }
}
```

---

## v2 LLM-judge (opt-in)

Daha akıllı puanlama için Haiku 4.5 ile değerlendirme:

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
```

Hook otomatik tespit eder. Yoksa regex fallback'e düşer (yine çalışır).

**Maliyet:** ~$0.0001/prompt. Ayda 1000 prompt için ~$0.10.

**Devre dışı bırakma:**
```bash
export PROMPTLINT_LLM=0   # rules-only zorla
```

---

## Standalone token counter

Chat'in dışında, ayrı terminal'de canlı dashboard:

```bash
python3 ~/bin/token-counter.py            # mevcut session'ı izle
python3 ~/bin/token-counter.py --new      # sadece bu komuttan sonra başlayan session (video için)
python3 ~/bin/token-counter.py --session <path>  # belirli JSONL dosyası
```

Gösterir:
- Context window doluluk (% kaç)
- Session toplamları (input / output / cache write / cache read)
- Tahmini maliyet (Opus / Sonnet / Haiku auto-detect)
- Live spinner + ● LIVE indikatörü

---

## Özelleştirme

`~/.claude/hooks/prompt-checker.py` üst kısmında:

```python
PASS_THRESHOLD  = 7   # >= → silent pass
BLOCK_THRESHOLD = 4   # <  → block

VAGUE_VERBS    = [...]   # belirsiz fiil regex listesi
ULTRA_LAZY     = [...]   # tek kelime komutlar
REFERENCE_PATTERNS = [...] # dosya/fonksiyon regex'leri
SCOPE_KEYWORDS = [...]   # "dokunma", "sadece"
FORMAT_KEYWORDS = [...]  # "tablo", "liste"
```

Kuralları kendi diline / projene göre düzenleyebilirsin.

---

## Skor formülü (rules mode)

| Boyut | Etki |
|-------|------|
| char_count < 8 OR word_count == 1 | -7 |
| char_count < 15 OR word_count == 2 | -5 |
| char_count < 40 | -2 |
| Ultra-lazy ("yap", "yapsana", "hadi") | -5 |
| Belirsiz fiil var | -3 |
| Spesifik referans yok | -2 |
| Kapsam (dokunma/sadece) yok | -1 |
| Format (tablo/liste) yok | -1 |

Başlangıç skoru: 10. Conversation continuation kelimeleri (`evet`, `tamam`, `devam`, vs.) silent pass.

---

## Klasör yapısı

```
promptlint/
├── install.sh
├── README.md
├── LICENSE                                 # MIT
├── .claude/
│   ├── settings.example.json
│   ├── hooks/
│   │   ├── prompt-checker.py               # ANA BEYİN — UserPromptSubmit
│   │   └── token-reporter.py               # OTOMATİK POP-UP — Stop
│   └── skills/
│       └── prompt-coach/
│           └── SKILL.md
├── tools/
│   └── token-counter.py                    # standalone CLI
├── assets/
│   └── cover.svg                           # README kapağı
└── examples/
    ├── 01-developer-prompts.md
    ├── 02-daily-prompts.md
    └── 03-formula.md
```

---

## Felsefe

Prompt yazmak bir **beceri**. Diğer beceriler gibi geri-bildirimle gelişir. `promptlint` sana **anlık** geri-bildirim verir; her prompttan öğrenirsin.

Token counter ise iddiayı kanıta çevirir:
> "İyi prompt yaz" → boş laf
> "İyi prompt yaz, bak ölçüyorum" → kanıt

---

## Lisans

MIT — bkz. `LICENSE`.

---

## Katkı

Issue aç, PR gönder, fork at. Vague prompt regex'lerine yenilerini eklemek özellikle değerli — kendi dilindeki "lazy verb" kalıplarını PR olarak gönder.
