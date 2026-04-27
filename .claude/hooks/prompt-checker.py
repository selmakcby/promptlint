#!/usr/bin/env python3
"""promptlint — UserPromptSubmit hook for Claude Code.

Reads the user's prompt from stdin (Claude Code passes it as JSON),
scores it 0-10 against simple heuristics, and:
  - score >= 7  → silent pass (good prompt)
  - score 4-6   → pass + inject coach note for Claude
  - score < 4   → block with user-facing feedback (exit 2)

Customize thresholds and rules below.
"""
import json
import re
import sys

# ─── thresholds ──────────────────────────────────────────────────────────────
PASS_THRESHOLD  = 7   # >= → silent pass
BLOCK_THRESHOLD = 4   # <  → block

# Skip very short conversation continuations (yes / no / continue / etc.)
CONTINUATIONS = {
    "evet", "yes", "y", "tamam", "ok", "okay", "devam", "continue",
    "go", "no", "n", "hayır", "hayir", "dur", "stop", "iptal", "cancel",
}

# ─── rules ───────────────────────────────────────────────────────────────────
VAGUE_VERBS = [
    # Turkish — konuşma dili kalıpları
    r"\bdüzelt\b", r"\btemizle\b", r"\biyileştir\b", r"\bbiraz\b",
    r"\bgüzel(leştir)?\b", r"\bdaha iyi\b", r"\bdüzenle\b",
    r"\bkodumu\b", r"\bher şey(i)?\b", r"\bhepsi(ni)?\b",
    r"\bşöyle bi\w*\b", r"\bbir şey(ler)?\b", r"\bbirşey(ler)?\b",
    r"\byapsa(na)?\b", r"\bhalleder?\s*mi\w*\b", r"\bhalledebilir mi\w*\b",
    r"\bne yapsam\b", r"\byardım(\s+eder)?(\s+mi\w*)?\b",
    r"\bşunu bir bak\b", r"\bşunu\b(?!\s+\w+\.\w)",  # şunu without a file ref
    r"\bbişey\w*\b", r"\bbi şey\w*\b",
    r"\bgüzel ol(sun|maz)\b", r"\bçirkin\b",
    r"\bçözer mi\w*\b", r"\bbakar mı\w*\b",
    # English (mixed-language Turkish devs)
    r"\bfix\b", r"\bclean(\s*up)?\b", r"\bimprove\b", r"\bmake\s+(it\s+)?better\b",
    r"\bnicer\b", r"\brefactor\s+everything\b", r"\bmy code\b",
    r"\bsomething\b", r"\bhelp me\b",
]

REFERENCE_PATTERNS = [
    r"\.(ts|tsx|js|jsx|py|md|json|yml|yaml|html|css|scss|go|rs|java|rb|sh|sql|xml|toml)\b",
    r"src/|/src/|/lib/|/components?/|/pages?/|/api/",
    r"\bclass\s+\w+|\bfunction\s+\w+|\bdef\s+\w+|\bcomponent\s+\w+|\bmethod\s+\w+",
    r"\bline\s*\d+|\d+\s*[-–]\s*\d+|:\d+",
]

SCOPE_KEYWORDS = [
    "dokunma", "sadece", "yalnızca", "yalnizca", "değiştirme", "degistirme",
    "hariç", "haric", "koru",
    "only", "don't touch", "do not", "except", "preserve", "keep",
]

FORMAT_KEYWORDS = [
    "tablo", "liste", "madde", "cümle", "kelime", "satır", "satir",
    "paragraf", "kısa", "kisa", "uzun",
    "table", "list", "bullet", "sentence", "word", "paragraph", "json",
    "markdown", "format", "schema",
]


# ─── analyzer ────────────────────────────────────────────────────────────────
def analyze(prompt: str) -> tuple[int, list[str]]:
    p = prompt.strip()
    p_lower = p.lower()
    score = 10
    issues: list[str] = []

    # Length
    L = len(p)
    if L < 15:
        score -= 5
        issues.append("Çok kısa — bağlam eksik (en az bir cümle yaz)")
    elif L < 40:
        score -= 2
        issues.append("Kısa — daha çok detay verebilirsin")

    # Vague verbs
    if any(re.search(pat, p_lower) for pat in VAGUE_VERBS):
        score -= 3
        issues.append("Belirsiz fiil — hangi dosya? hangi pattern? hangi standart?")

    # Specific reference (file / function / line)
    has_ref = any(re.search(pat, p, re.IGNORECASE) for pat in REFERENCE_PATTERNS)
    if not has_ref and L > 15:
        score -= 2
        issues.append("Spesifik referans yok — dosya, fonksiyon, satır numarası ekle")

    # Scope / exclusion
    if not any(k in p_lower for k in SCOPE_KEYWORDS) and score < 9 and L > 20:
        score -= 1
        issues.append("Kapsam belirsiz — neye DOKUNMASIN, neye SADECE odaklansın?")

    # Output format
    if not any(k in p_lower for k in FORMAT_KEYWORDS) and L > 30:
        score -= 1
        issues.append("Format yok — uzunluk/yapı belirt (kaç cümle, tablo, liste)")

    return max(0, score), issues


# ─── messaging ───────────────────────────────────────────────────────────────
def block_message(score: int, issues: list[str], original: str) -> str:
    bullets = "\n".join(f"  • {i}" for i in issues)
    snippet = (original[:60] + "...") if len(original) > 60 else original
    return f"""
🚨 PROMPTLINT — Skor: {score}/10  (eşik: {BLOCK_THRESHOLD})

Sorunlar:
{bullets}

Önerilen format:
  → DOSYA / KAPSAM   (src/auth/login.ts:42-78)
  → AKSIYON          (validatePassword'ı zod schema ile refactor et)
  → SINIRLAR         (test dosyalarına dokunma, regex'i koru)
  → ÇIKTI            (sadece değişen satırları göster)

Şu an yazdığın:
  "{snippet}"

Promptu yeniden yaz, devam edeceğim.
""".strip()


def coach_note(score: int, issues: list[str]) -> str:
    bullets = "; ".join(issues)
    return (
        f"[PROMPTLINT NOTE — kullanıcı promptu zayıf (skor {score}/10). "
        f"Cevap üretmeden ÖNCE şu belirsizlikleri kullanıcıya sor: {bullets}. "
        f"Varsayım yapmadan netleştir, sonra çalış.]"
    )


# ─── main ────────────────────────────────────────────────────────────────────
def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}

    prompt = payload.get("prompt") or payload.get("user_prompt") or raw
    prompt = (prompt or "").strip()

    if not prompt:
        return 0

    # Skip continuation words ("evet", "ok", "devam", ...)
    words = prompt.lower().split()
    if len(words) <= 3 and any(w.strip(".,!?") in CONTINUATIONS for w in words):
        return 0

    score, issues = analyze(prompt)

    if score >= PASS_THRESHOLD:
        return 0  # silent pass

    if score >= BLOCK_THRESHOLD:
        # Visible warning to user (stderr)
        short = "; ".join(issues[:2])
        print(
            f"🟡 PROMPTLINT — Skor: {score}/10  ·  Claude netleştirici sorular soracak\n"
            f"   ↳ {short}",
            file=sys.stderr,
        )
        # Coach note for Claude (stdout — gets injected as context)
        print(coach_note(score, issues))
        return 0

    # Block
    print(block_message(score, issues, prompt), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
