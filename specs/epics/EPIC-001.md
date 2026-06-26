# Epic: SimpleRename — Book PDF Organizer
**ID:** EPIC-001
**Status:** Active
**Owner:** PP-Planner
**Target Quarter:** Q3 2026

---

## Goal

Transformar o SimpleRename de um renomeador genérico de arquivos em uma ferramenta especializada para
organização de bibliotecas pessoais de livros em PDF, capaz de extrair metadados automaticamente,
consultar bases bibliográficas online e sugerir nomes e estruturas de pastas baseadas em padrões
internacionais de biblioteconomia — tudo através de uma interface de planilha editável que o usuário
já conhece.

---

## Contexto e Motivação

Usuários que acumulam centenas ou milhares de PDFs de livros enfrentam um problema crônico: arquivos
com nomes inúteis como `documento(3).pdf`, `ebook_final_v2.pdf` ou `9788535902778.pdf`. As soluções
existentes são ou excessivamente complexas (Calibre) ou focadas em outros domínios (artigos científicos,
documentos corporativos). Não existe uma ferramenta leve, nativa para Windows, com interface visual
intuitiva e foco exclusivo em livros.

---

## Referências de Mercado Pesquisadas

| Ferramenta | Abordagem | Limitação |
|---|---|---|
| [Calibre](https://calibre-ebook.com) | Gestão completa de ebooks | Ecossistema pesado, não é só renomeador |
| [pdf-renamer (MicheleCotrufo)](https://github.com/MicheleCotrufo/pdf-renamer) | DOI + busca online | Focado em artigos científicos, não livros |
| [AI-PDF-Renamer (Web3NL)](https://github.com/Web3NL/AI-PDF-Renamer) | Google Gemini Vision | Requer API paga, sem GUI de planilha |
| [ebook_renamer](https://github.com/agilecreativity/ebook_renamer) | Metadados embutidos | Apenas CLI, sem preview ou edição |
| [autorename-pdf](https://github.com/ptmrio/autorename-pdf) | IA para documentos corporativos | Não entende estrutura de livros |

**Diferencial do SimpleRename:** combina extração automática + lookup online + interface de planilha
editável + padrões de biblioteconomia em uma única ferramenta leve para Windows.

---

## Success Metrics

| Métrica | Baseline | Target |
|---|---|---|
| Metadados extraídos automaticamente (sem intervenção) | 0% | ≥ 70% dos PDFs com metadado embutido |
| Taxa de acerto na busca online (título correto sugerido) | 0% | ≥ 80% quando ISBN presente |
| Tempo médio para renomear 50 arquivos | ~30 min manual | < 5 min com automação |
| Builds Windows gerados automaticamente por tag git | 0 | 100% das releases |

---

## Features deste Epic

| Feature | Prioridade | Status | Agente |
|---|---|---|---|
| FEATURE-001: Build Pipeline & Windows Installer | P0 | Draft | Architect + Developer |
| FEATURE-002: Extração de Metadados de PDF | P0 | Draft | Developer |
| FEATURE-003: Busca Online (Google Books / Open Library) | P1 | Draft | Developer |
| FEATURE-004: Estratégia de Biblioteconomia e Catalogação | P1 | Draft | Developer |
| FEATURE-005: Planilha Editável com Preview e Undo | P1 | Draft | Developer |

---

## Milestones

| Milestone | Data Alvo | Critério de Saída |
|---|---|---|
| M1: Build Automatizado | Semana 2 | `git tag v1.0.0` → `.exe` gerado pelo CI em < 10 min |
| M2: Metadados Locais | Semana 4 | Carregar pasta → colunas Título/Autor/ISBN preenchidas automaticamente para ≥ 70% dos PDFs |
| M3: Lookup Online | Semana 6 | Botão "Buscar Online" → campos preenchidos via API para PDFs sem metadado embutido |
| M4: Catalogação | Semana 8 | Sugestão automática de pasta (CDD) ao lado do novo nome |
| M5: Planilha Completa | Semana 9 | Preview + Ctrl+Z/Y funcionando; zero regressões nos testes |

---

## Dependências Externas

- Open Library API: `https://openlibrary.org/api/books` (gratuita, sem chave)
- Google Books API: `https://www.googleapis.com/books/v1/volumes` (gratuita até 1000 req/dia, chave opcional)
- PyMuPDF (fitz): leitura de metadados de PDF
- PyInstaller: geração do executável Windows
- NSIS: empacotamento do installer

---

## Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| PDFs sem metadados embutidos | Alta | Médio | Fallback para OCR da capa ou busca por nome do arquivo |
| Rate limit das APIs | Baixa | Baixo | Cache local de resultados por ISBN/título |
| Build Windows falha no CI (cross-compile) | Média | Alto | Usar GitHub Actions com `windows-latest` runner |
| Conflito fill handle duplo (bug existente) | Alta | Médio | Resolver como pré-requisito de FEATURE-005 |
