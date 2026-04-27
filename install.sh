#!/usr/bin/env bash
# promptlint installer
# Copies hook + skill + token-counter into ~/.claude and ~/bin

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

# 1. Hook
mkdir -p "${CLAUDE_DIR}/hooks"
cp .claude/hooks/prompt-checker.py "${CLAUDE_DIR}/hooks/"
chmod +x "${CLAUDE_DIR}/hooks/prompt-checker.py"
echo -e "${green}✓${reset} hook  → ${CLAUDE_DIR}/hooks/prompt-checker.py"

# 2. Skill
mkdir -p "${CLAUDE_DIR}/skills/prompt-coach"
cp .claude/skills/prompt-coach/SKILL.md "${CLAUDE_DIR}/skills/prompt-coach/"
echo -e "${green}✓${reset} skill → ${CLAUDE_DIR}/skills/prompt-coach/"

# 3. Token counter
mkdir -p "${BIN_DIR}"
cp tools/token-counter.py "${BIN_DIR}/"
chmod +x "${BIN_DIR}/token-counter.py"
echo -e "${green}✓${reset} counter → ${BIN_DIR}/token-counter.py"

echo
echo -e "${yellow}▸ MANUEL ADIM — settings.json'a ekle:${reset}"
echo
echo -e "${dim}Şu içeriği ${CLAUDE_DIR}/settings.json'daki 'hooks' bloğuna merge et${reset}"
echo -e "${dim}(eğer hooks bloğu yoksa, root level'a 'hooks' anahtarı altına yapıştır):${reset}"
echo
cat .claude/settings.example.json
echo
echo -e "${cyan}▸ TEST:${reset}"
echo "  claude"
echo "  > kodumu temizle"
echo "  ↳ promptlint hook'u devreye girmeli"
echo
echo -e "${cyan}▸ TOKEN COUNTER:${reset}"
echo "  python3 ${BIN_DIR}/token-counter.py --new"
echo
echo -e "${green}Kurulum bitti.${reset}"
echo
