# Feature: Build Pipeline & Windows Installer Automatizado
**ID:** FEATURE-001
**Epic:** EPIC-001
**Status:** Draft
**Priority:** P0 (blocker)
**Author:** PP-Planner
**Created:** 2026-06-25

---

## Problem Statement

Hoje o SimpleRename não tem processo de build reproduzível. O executável em `dist-windows/` foi gerado
manualmente e não há garantia de que um novo desenvolvedor ou um novo ambiente consiga replicar o
resultado. Não existe versionamento semântico, não há instalador que atualize uma versão existente,
e o processo de release é totalmente manual. Isso torna impossível distribuir o software com confiança
ou manter um histórico de versões.

## Proposed Solution

Implementar um pipeline de CI/CD usando **GitHub Actions** com runner `windows-latest`, que dispara
automaticamente ao criar uma tag git semântica (`v1.x.x`). O pipeline usa **PyInstaller** para gerar
o `.exe` e **NSIS** para empacotar um instalador que detecta versão existente e faz upgrade ou
instalação limpa conforme necessário. A versão é injetada automaticamente no executável a partir da
tag git.

## Users & Personas

- **Primário:** Lucas (mantenedor) — quer criar uma release sem precisar lembrar comandos manuais
- **Secundário:** usuário final Windows — quer instalar/atualizar com um duplo-clique

## User Stories

- Como mantenedor, quero que ao criar a tag `v1.2.0` no git um instalador Windows seja gerado
  automaticamente, para que eu não precise rodar comandos de build manualmente.
- Como mantenedor, quero que o número de versão apareça no título da janela e no "Sobre", para
  que usuários saibam qual versão estão usando.
- Como usuário final, quero que o instalador detecte uma versão anterior e a atualize sem precisar
  desinstalar manualmente, para que meu processo seja simples.
- Como usuário final, quero que o instalador crie atalho no Desktop e no Menu Iniciar, para
  acessar o programa facilmente.

## Acceptance Criteria

- [ ] `git tag v1.0.0 && git push --tags` dispara o pipeline no GitHub Actions
- [ ] O pipeline termina em menos de 10 minutos e publica o `.exe` como GitHub Release asset
- [ ] O instalador gerado pelo NSIS detecta versão anterior instalada e oferece upgrade
- [ ] O instalador cria atalho no Desktop e em `%APPDATA%\Microsoft\Windows\Start Menu`
- [ ] O título da janela exibe `Simple Rename v1.0.0`
- [ ] O arquivo `src/version.py` é a única fonte de verdade da versão, lido pelo `setup.py` e pela UI
- [ ] Build falha com erro claro se dependências do `requirements.txt` não forem satisfeitas
- [ ] O `.exe` gerado roda em Windows 10 e 11 sem instalação prévia de Python

## Out of Scope

- Auto-update dentro da aplicação (checar nova versão ao abrir) — deferido para versão futura
- Build para macOS ou Linux
- Assinatura digital do executável (code signing) — deferido por custo

## Dependencies

- Depends on: Repositório no GitHub com Actions habilitado
- Blocks: FEATURE-002, FEATURE-003, FEATURE-004, FEATURE-005 (todas precisam de build funcional para testar)

## Detalhamento Técnico

### Estrutura de Arquivos Necessários

```
simplerename/
├── src/
│   └── version.py          ← NOVO: única fonte de verdade da versão
├── .github/
│   └── workflows/
│       └── build-release.yml  ← NOVO: pipeline CI/CD
├── installer.nsi           ← ATUALIZAR: ler versão do version.py
├── build_windows.bat       ← SUBSTITUIR pelo pipeline (manter para dev local)
└── requirements.txt        ← CONGELAR versões exatas (pip freeze)
```

### `src/version.py`
```python
__version__ = "1.0.0"
APP_NAME = "Simple Rename"
```

### `.github/workflows/build-release.yml` (estrutura)
```yaml
name: Build Windows Release
on:
  push:
    tags: ['v*.*.*']
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: pip install pyinstaller
      - run: pyinstaller --onefile --windowed --icon=resources/icons/simplerename.ico
               --name SimpleRename main.py
      - name: Build NSIS Installer
        uses: joncloud/makensis-action@v4
        with: { script-file: installer.nsi }
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/SimpleRename.exe
            SimpleRename-Setup.exe
```

### Versionamento Semântico

| Tipo de mudança | Exemplo de tag | Quando usar |
|---|---|---|
| Breaking change | `v2.0.0` | Mudança de comportamento incompatível |
| Nova feature | `v1.1.0` | Nova funcionalidade adicionada |
| Bugfix | `v1.0.1` | Correção sem nova funcionalidade |

## Open Questions

- [ ] O repositório GitHub já existe público ou é privado? (afeta permissões do Actions)
- [ ] Qual Python mínimo suportar? (3.10, 3.11 ou 3.12)
- [ ] O NSIS já presente no projeto (`installer.nsi` e `windows_installer.nsi`) — qual dos dois é o definitivo?
