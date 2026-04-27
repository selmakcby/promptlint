#!/usr/bin/env python3
"""promptlint — UserPromptSubmit hook for Claude Code.

Hybrid prompt grader:
  Stage 1: cheap rules (continuation, ultra-short, ultra-lazy)  → instant decisions
  Stage 2: Haiku LLM-judge (if anthropic SDK + API key)         → smart grading
  Stage 3: regex fallback                                       → if LLM unavailable

Toggle commands (typed as a prompt):
  :lint off   →  disables hook (state file: ~/.claude/promptlint.disabled)
  :lint on    →  re-enables hook

Customize thresholds and rules below.
"""
import json
import os
import re
import sys
from pathlib import Path

# ─── thresholds ──────────────────────────────────────────────────────────────
PASS_THRESHOLD  = 7
BLOCK_THRESHOLD = 4

STATE_FILE = Path.home() / ".claude" / "promptlint.disabled"

# Skip continuation prompts
CONTINUATIONS = {
    "evet", "yes", "y", "tamam", "ok", "okay", "devam", "continue",
    "go", "no", "n", "hayır", "hayir", "dur", "stop", "iptal", "cancel",
}

# Toggle commands
TOGGLE_OFF = {":lint off", ":lint kapat", "/lint off", "/promptlint off"}
TOGGLE_ON  = {":lint on", ":lint ac", ":lint aç", "/lint on", "/promptlint on"}

# ─── rules ───────────────────────────────────────────────────────────────────
VAGUE_VERBS = [
    r"\bdüzelt\b", r"\btemizle\b", r"\biyileştir\b", r"\bbiraz\b",
    r"\bgüzel(leştir)?\b", r"\bdaha iyi\b", r"\bdüzenle\b",
    r"\bkodumu\b", r"\bher şey(i)?\b", r"\bhepsi(ni)?\b",
    r"\bşöyle bi\w*\b", r"\bbir şey(ler)?\b", r"\bbirşey(ler)?\b",
    r"\bhalleder?\s*mi\w*\b", r"\bhalledebilir mi\w*\b",
    r"\bne yapsam\b", r"\byardım(\s+eder)?(\s+mi\w*)?\b",
    r"\bşunu bir bak\b",
    r"\bbişey\w*\b", r"\bbi şey\w*\b",
    r"\bgüzel ol(sun|maz)\b", r"\bçirkin\b",
    r"\bçözer mi\w*\b", r"\bbakar mı\w*\b",
    r"\bfix\b", r"\bclean(\s*up)?\b", r"\bimprove\b", r"\bmake\s+(it\s+)?better\b",
    r"\bnicer\b", r"\brefactor\s+everything\b", r"\bmy code\b",
    r"\bsomething\b", r"\bhelp me\b",
]

ULTRA_LAZY = [
    r"^\s*yap(\s*art[iı]?k)?\s*[!.?]*\s*$",
    r"^\s*yapsana\s*[!.?]*\s*$",
    r"^\s*hadi(\s+yap)?\s*[!.?]*\s*$",
    r"^\s*olsun\s*[!.?]*\s*$",
    r"^\s*yine de\s+yap\s*[!.?]*\s*$",
    r"^\s*do it\s*[!.?]*\s*$",
    r"^\s*just do it\s*[!.?]*\s*$",
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


# ─── rules-based analyzer (fallback) ─────────────────────────────────────────
def analyze_rules(prompt: str) -> tuple[int, list[str]]:
    p = prompt.strip()
    p_lower = p.lower()
    score = 10
    issues: list[str] = []

    char_count = len(p)
    word_count = len(p.split())

    if char_count < 8 or word_count == 1:
        score -= 7
        issues.append("Çok kısa — tek kelime/komut, bağlam yok")
    elif char_count < 15 or word_count == 2:
        score -= 5
        issues.append("Çok kısa — daha çok detay verebilirsin")
    elif char_count < 40:
        score -= 2
        issues.append("Yetersiz — bağlam genişletilebilir")

    if any(re.search(pat, p_lower) for pat in ULTRA_LAZY):
        score -= 5
        issues.append("Sadece komut — bağlam yok ('yap'/'yapsana'/'hadi' tek başına)")

    if any(re.search(pat, p_lower) for pat in VAGUE_VERBS):
        score -= 3
        issues.append("Belirsiz fiil — hangi dosya? hangi pattern? hangi standart?")

    has_ref = any(re.search(pat, p, re.IGNORECASE) for pat in REFERENCE_PATTERNS)
    if not has_ref and char_count > 15:
        score -= 2
        issues.append("Spesifik referans yok — dosya, fonksiyon, satır numarası ekle")

    if not any(k in p_lower for k in SCOPE_KEYWORDS) and score < 9 and char_count > 20:
        score -= 1
        issues.append("Kapsam belirsiz — neye DOKUNMASIN, neye SADECE odaklansın?")

    if not any(k in p_lower for k in FORMAT_KEYWORDS) and char_count > 30:
        score -= 1
        issues.append("Format yok — uzunluk/yapı belirt (kaç cümle, tablo, liste)")

    return max(0, score), issues


# ─── LLM judge (Haiku) ───────────────────────────────────────────────────────
def analyze_llm(prompt: str) -> tuple[int, list[str]] | None:
    """Use Haiku to grade prompt. Returns None if SDK/key missing."""
    if os.environ.get("PROMPTLINT_LLM") == "0":
        return None
    try:
        import anthropic
    except ImportError:
        return None
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None

    client = anthropic.Anthropic()
    rubric = f"""Sen Claude Code prompt kalite uzmanısın. Kullanıcı promptunu 0-10 arası değerlendir.

Prompt: "{prompt[:2000]}"

5 boyut, her biri 0-2 puan:
1. SPESİFİKLİK — dosya/fonksiyon/satır referansı?
2. AKSIYON — ne yapılacağı net mi?
3. SINIRLAR — ne dokunulmayacağı belli mi?
4. FORMAT — çıktı formatı belirtilmiş mi?
5. BAĞLAM — yeterli arka plan var mı?

ÖNEMLİ: Uzun ama belirsiz prompt, kısa ama spesifik prompt'tan DAHA AZ puan alır. Verbosity bias'a düşme.

Sadece bu JSON'u döndür (başka hiçbir şey yazma):
{{"score": <int 0-10>, "issues": ["kısa madde 1", "kısa madde 2"]}}"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=300,
            messages=[{"role": "user", "content": rubric}],
        )
        text = response.content[0].text
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group())
        score = int(data.get("score", 5))
        issues = [str(i) for i in data.get("issues", [])][:5]
        return max(0, min(10, score)), issues
    except Exception:
        return None


def analyze(prompt: str) -> tuple[int, list[str], str]:
    """Returns (score, issues, source). source = 'rules' or 'llm'."""
    # Try LLM first if available
    llm_result = analyze_llm(prompt)
    if llm_result is not None:
        score, issues = llm_result
        return score, issues, "llm"
    # Fallback to rules
    score, issues = analyze_rules(prompt)
    return score, issues, "rules"


# ─── messaging ───────────────────────────────────────────────────────────────
def block_message(score: int, issues: list[str], original: str, source: str) -> str:
    bullets = "\n".join(f"  • {i}" for i in issues)
    snippet = (original[:60] + "...") if len(original) > 60 else original
    badge = "🤖 LLM" if source == "llm" else "📐 RULES"
    return f"""
🚨 PROMPTLINT — Skor: {score}/10  ({badge})

Sorunlar:
{bullets}

Önerilen format:
  → DOSYA / KAPSAM   (src/auth/login.ts:42-78)
  → AKSIYON          (validatePassword'ı zod schema ile refactor et)
  → SINIRLAR         (test dosyalarına dokunma, regex'i koru)
  → ÇIKTI            (sadece değişen satırları göster)

Şu an yazdığın:
  "{snippet}"

İpucu: filtreyi kapatmak istersen :lint off yaz
""".strip()


def coach_note(score: int, issues: list[str], source: str) -> str:
    bullets = "; ".join(issues)
    return (
        f"[PROMPTLINT NOTE — kullanıcı promptu zayıf (skor {score}/10, {source}). "
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

    p_lower = prompt.lower()

    # Toggle commands — handled FIRST, before any other logic
    if p_lower in TOGGLE_OFF:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.touch()
        print("🔕 promptlint kapatıldı. Tekrar açmak için: :lint on", file=sys.stderr)
        return 2  # block (don't send to Claude)
    if p_lower in TOGGLE_ON:
        STATE_FILE.unlink(missing_ok=True)
        print("🔔 promptlint açıldı. Kapatmak için: :lint off", file=sys.stderr)
        return 2

    # If state file says disabled → silent pass
    if STATE_FILE.exists():
        return 0

    # Continuation skip
    words = p_lower.split()
    if len(words) <= 3 and any(w.strip(".,!?") in CONTINUATIONS for w in words):
        return 0

    score, issues, source = analyze(prompt)

    if score >= PASS_THRESHOLD:
        return 0

    if score >= BLOCK_THRESHOLD:
        short = "; ".join(issues[:2])
        badge = "🤖 LLM" if source == "llm" else "📐 RULES"
        print(
            f"🟡 PROMPTLINT — Skor: {score}/10  ({badge})  ·  Claude netleştirici sorular soracak\n"
            f"   ↳ {short}",
            file=sys.stderr,
        )
        print(coach_note(score, issues, source))
        return 0

    # Block
    print(block_message(score, issues, prompt, source), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
