#!/usr/bin/env bash
# promptlint installer
set -e

CLAUDE_DIR="${HOME}/.claude"
BIN_DIR="${HOME}/bin"

cyan='\033[0;36m'
green='\033[0;32m'
yellow='\033[0;33m'
dim='\033[2m'
reset='\033[0m'

echo
echo -e "${cyan}▸ promptlint kuruluyor...${reset}"
echo

# 1. Hooks (prompt-checker + token-reporter)
mkdir -p "${CLAUDE_DIR}/hooks"
cp .claude/hooks/prompt-checker.py "${CLAUDE_DIR}/hooks/"
cp .claude/hooks/token-reporter.py "${CLAUDE_DIR}/hooks/"
chmod +x "${CLAUDE_DIR}/hooks/prompt-checker.py" "${CLAUDE_DIR}/hooks/token-reporter.py"
echo -e "${green}✓${reset} hooks  → ${CLAUDE_DIR}/hooks/{prompt-checker,token-reporter}.py"

# 2. Skill
mkdir -p "${CLAUDE_DIR}/skills/prompt-coach"
cp .claude/skills/prompt-coach/SKILL.md "${CLAUDE_DIR}/skills/prompt-coach/"
echo -e "${green}✓${reset} skill  → ${CLAUDE_DIR}/skills/prompt-coach/"

# 3. Token counter (standalone CLI)
mkdir -p "${BIN_DIR}"
cp tools/token-counter.py "${BIN_DIR}/"
chmod +x "${BIN_DIR}/token-counter.py"
echo -e "${green}✓${reset} counter → ${BIN_DIR}/token-counter.py"

# 4. Optional: Anthropic SDK for v2 LLM-judge
echo
echo -e "${cyan}▸ v2 (Haiku LLM-judge) için opsiyonel:${reset}"
if python3 -c "import anthropic" 2>/dev/null; then
  echo -e "${green}✓${reset} anthropic SDK zaten kurulu"
else
  echo -e "${yellow}!${reset} anthropic SDK yok. Yüklemek için:"
  echo -e "  ${dim}pip install anthropic${reset}"
  echo -e "  ${dim}export ANTHROPIC_API_KEY=...${reset}"
  echo -e "  ${dim}(Yüklü değilse promptlint regex fallback'e düşer — hâlâ çalışır)${reset}"
fi

echo
echo -e "${yellow}▸ MANUEL ADIM — settings.json'a ekle:${reset}"
echo -e "${dim}${CLAUDE_DIR}/settings.json'daki 'hooks' bloğuna UserPromptSubmit ve Stop'u merge et:${reset}"
echo
cat .claude/settings.example.json
echo
echo -e "${cyan}▸ TEST:${reset}"
echo "  claude"
echo "  > kodumu temizle           ← 🚨 BLOK 0/10 görmeli"
echo "  > :lint off                ← filtreyi kapat"
echo "  > :lint on                 ← filtreyi tekrar aç"
echo
echo -e "${cyan}▸ TOKEN COUNTER (standalone):${reset}"
echo "  python3 ${BIN_DIR}/token-counter.py --new"
echo
echo -e "${cyan}▸ OTOMATİK POP-UP:${reset}"
echo -e "${dim}Stop hook her cevaptan sonra ekrana token kutusu çizer.${reset}"
echo
echo -e "${green}Kurulum bitti.${reset}"
echo
