# FEATURE-001 — Build Pipeline

**Status:** In Progress
**Epic:** EPIC-001
**Semanas:** 1-2 (Q3 2026)

## Descrição

Configurar o pipeline de build automatizado para gerar o instalador Windows a partir do GitHub Actions.

## Entregáveis

- [x] `src/version.py` — única fonte de verdade da versão (`1.0.0`)
- [x] `.github/workflows/build-release.yml` — CI/CD com PyInstaller + NSIS
- [x] `installer.nsi` — suporte a `/DVERSION=X.Y.Z` via `!ifndef VERSION` guard
- [x] `requirements.txt` — versões congeladas (sem `>=` ou `~=`)
- [x] `main.py` — título da janela exibe `APP_NAME v__version__`
- [x] `scripts/` — scripts legados movidos para fora da raiz (`build_windows.bat`, `wine_compile.py`, `windows_build.bat`)
- [x] DEBT-005 resolvido — `windows_installer.nsi` duplicado removido

## Decisões

- ADR-001: PyInstaller + NSIS + GitHub Actions `windows-latest`
- Tag `v1.0.0` no git dispara o build automaticamente

## Dependências

Nenhuma (desbloqueador de todas as outras features).

## Próximo passo

Criar tag `v1.0.0` e verificar que o workflow do GitHub Actions gera o artefato `SimpleRename-Setup-1.0.0.exe`.
