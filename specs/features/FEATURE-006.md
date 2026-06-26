# Feature: Layout Dual-Faixa — Estado Atual vs. Proposta de Mudança
**ID:** FEATURE-006
**Epic:** EPIC-001
**Status:** In Progress
**Priority:** P1 (critical)
**Author:** PP-Planner
**Created:** 2026-06-26

---

## Problem Statement

A planilha atual exibe todos os campos numa única faixa visual sem distinção entre o que o arquivo
**é** e o que ele **deveria se tornar**. O resultado é que o usuário não sabe o que já está gravado
no arquivo, o que foi extraído automaticamente, o que é uma sugestão do sistema e o que ele mesmo
editou. Isso gera insegurança: o usuário teme clicar em "Apply Changes" sem ter clareza do que será
alterado. Além disso, colunas como "Editora" frequentemente exibem lixo de metadado (ex: "Microsoft®")
sem nenhum indicador de qualidade, e não há distinção visual entre campos read-only e campos editáveis.

## Proposed Solution

Separar a planilha em duas faixas coloridas com cabeçalhos visuais distintos:

- **Faixa Azul — Estado Atual (read-only):** Nome do arquivo, Formato, Título atual, Autor atual,
  ISBN detectado, Ano atual, Editora atual. Estas colunas refletem o que está gravado no arquivo
  agora. O usuário não edita aqui — apenas lê.
- **Faixa Verde — Proposta de Mudança (editável):** Novo Nome do Arquivo, Novo Título, Novo Autor,
  Novo Ano, Nova Editora. Estas colunas recebem sugestões do sistema (vindas da busca online ou de
  inferência local) e podem ser editadas livremente antes de aplicar.

Um indicador de qualidade por linha (círculo colorido: 🟢🟡🔴) resume a completude dos metadados
atuais. Cada célula da faixa verde tem um badge de origem (arquivo, Open Library, Google Books,
manual) para o usuário saber de onde veio cada sugestão.

## Users & Personas

- **Primário:** Lucas — quer ver claramente o que o arquivo tem agora e o que vai mudar, campo a campo
- **Secundário:** qualquer usuário processando lote grande, onde revisar campo por campo é necessário
  para confiança antes de aplicar em massa

## User Stories

- Como usuário, quero ver uma faixa azul read-only com os dados atuais do arquivo (o que está
  gravado agora) separada visualmente de uma faixa verde editável com as sugestões de mudança, para
  saber exatamente o que vou alterar.
- Como usuário, quero um indicador visual por linha (verde/amarelo/vermelho) resumindo a qualidade
  dos metadados atuais, para saber rapidamente quais arquivos precisam de atenção.
- Como usuário, quero ver um badge de origem em cada célula da faixa verde (ex: "OL" para Open
  Library, "GB" para Google Books, "✎" para manual), para saber de onde veio a sugestão e decidir
  se confio nela.
- Como usuário, quero que células da faixa verde com sugestão pendente de confirmação tenham um
  fundo âmbar diferente de células já confirmadas (fundo branco), para saber o que ainda precisa
  de revisão.
- Como usuário, quero que a coluna "Preview" (nome final com extensão) seja calculada em tempo real
  a partir do campo "Novo Nome do Arquivo", para confirmar o resultado exato antes de aplicar.

## Acceptance Criteria

### Layout visual
- [ ] Cabeçalho de grupo "Estado Atual" sobre as colunas azuis, "Proposta de Mudança" sobre as verdes
- [ ] Colunas azuis têm fundo `#E6F1FB` (azul claro) e são não-editáveis (flags `Qt.ItemFlag`)
- [ ] Colunas verdes têm fundo `#EAF3DE` (verde claro) e aceitam edição
- [ ] Uma coluna separadora visível (2px) divide as duas faixas
- [ ] Coluna "⬤" (qualidade) é a primeira coluna, com ícone colorido por linha:
  - 🟢 verde: título + autor + (ISBN ou ano) presentes
  - 🟡 amarelo: pelo menos título OU autor presentes
  - 🔴 vermelho: nenhum campo útil disponível

### Colunas da faixa azul (read-only)
- [ ] Nome atual (nome do arquivo em disco, sem extensão)
- [ ] Formato (extensão: pdf, epub, mobi)
- [ ] Título atual (extraído pelo FEATURE-002 ou vazio)
- [ ] Autor atual
- [ ] ISBN detectado (normalizado para ISBN-13 ou vazio)
- [ ] Ano atual
- [ ] Editora atual

### Colunas da faixa verde (editável)
- [ ] Novo Nome do Arquivo (editável; sugere nome no padrão ABNT por padrão)
- [ ] Novo Título (editável)
- [ ] Novo Autor (editável)
- [ ] Novo Ano (editável)
- [ ] Nova Editora (editável)
- [ ] Preview (read-only calculado: `{Novo Nome do Arquivo}.{extensão}`)

### Badges de origem
- [ ] Badge "PDF" quando valor veio dos metadados embutidos do arquivo
- [ ] Badge "OL" quando veio do Open Library
- [ ] Badge "GB" quando veio do Google Books
- [ ] Badge "✎" quando foi editado manualmente pelo usuário
- [ ] Ausência de badge indica campo vazio (aguardando busca)

### Estados de célula da faixa verde
- [ ] Fundo âmbar claro: campo tem sugestão automática ainda não confirmada
- [ ] Fundo branco: campo vazio (aguarda busca ou entrada manual)
- [ ] Fundo verde claro: campo confirmado (usuário editou ou aceitou explicitamente)
- [ ] Fundo vermelho claro: campo com erro de validação (ex: ano com 5 dígitos)

### Toolbar
- [ ] Botão "Confirmar Linha" (checkmark) aceita todas as sugestões da linha selecionada
- [ ] Botão "Limpar Proposta" (X) apaga a faixa verde da linha sem alterar a faixa azul
- [ ] Botão "Confirmar Todos" aceita todas as sugestões de todas as linhas de uma vez
- [ ] Undo/Redo afetam apenas operações de rename aplicadas, não edições na planilha

## Out of Scope

- Modo de visualização "compacto" (esconder faixa azul) — deferido
- Edição inline de colunas da faixa azul (alterar metadados sem rename) — deferido
- Diff visual linha a linha mostrando o que mudou em cor diff (estilo git) — deferido para v2

## Dependencies

- Depends on: FEATURE-002 (popula faixa azul), FEATURE-003 (popula faixa verde via busca)
- Depends on: FEATURE-005 (coluna Preview já existe; aqui é integrada ao novo layout)
- Blocks: FEATURE-007 (busca ISBN precisa saber em quais células verde escrever)

## Detalhamento Técnico

### Modelo de dados por linha

```python
@dataclass
class FileRow:
    # Faixa azul (read-only — estado atual)
    current_filename:  str
    file_extension:    str
    current_title:     Optional[str]
    current_author:    Optional[str]
    current_isbn:      Optional[str]
    current_year:      Optional[str]
    current_publisher: Optional[str]
    metadata_quality:  MetadataQuality   # GREEN / YELLOW / RED

    # Faixa verde (editável — proposta)
    new_filename:      Optional[str] = None
    new_title:         Optional[str] = None
    new_author:        Optional[str] = None
    new_year:          Optional[str] = None
    new_publisher:     Optional[str] = None

    # Controle interno
    field_origins:     Dict[str, str] = field(default_factory=dict)
    # ex: {"new_title": "OL", "new_author": "GB", "new_year": "PDF"}
    field_confirmed:   Dict[str, bool] = field(default_factory=dict)
    # ex: {"new_title": True, "new_author": False}

    @property
    def preview(self) -> str:
        name = self.new_filename or self.current_filename
        return f"{name}{self.file_extension}"
```

### FileTableModel — flags por coluna

```python
BLUE_COLS  = [COL_QUALITY, COL_CURR_NAME, COL_FORMAT, COL_CURR_TITLE,
              COL_CURR_AUTHOR, COL_CURR_ISBN, COL_CURR_YEAR, COL_CURR_PUB]
GREEN_COLS = [COL_NEW_NAME, COL_NEW_TITLE, COL_NEW_AUTHOR,
              COL_NEW_YEAR, COL_NEW_PUB]
PREVIEW_COL = COL_PREVIEW   # read-only, calculado

def flags(self, index: QModelIndex) -> Qt.ItemFlags:
    col = index.column()
    if col in BLUE_COLS or col == PREVIEW_COL:
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
    return (Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable)
```

### FileTableModel — cores por estado

```python
def data(self, index, role=Qt.ItemDataRole.DisplayRole):
    col = index.column()
    row_data = self.rows[index.row()]

    if role == Qt.ItemDataRole.BackgroundRole:
        if col in BLUE_COLS:
            return QColor(230, 241, 251)   # azul claro #E6F1FB
        if col == PREVIEW_COL:
            return QColor(238, 238, 238)   # cinza neutro
        # Faixa verde: cor por estado
        field_key = GREEN_COL_KEYS[col]
        if row_data.field_confirmed.get(field_key):
            return QColor(234, 243, 222)   # verde confirmado
        if getattr(row_data, field_key) is not None:
            return QColor(250, 238, 218)   # âmbar (sugerido, pendente)
        return QColor(255, 255, 255)       # branco (vazio)
```

### Cabeçalho de grupo (QHeaderView customizado)

```python
class GroupedHeaderView(QHeaderView):
    """Renderiza duas linhas de cabeçalho: grupo (azul/verde) + nome da coluna."""

    GROUPS = [
        ("Estado Atual",       BLUE_COLS,    QColor(181, 212, 244)),
        ("Proposta de Mudança", GREEN_COLS,  QColor(159, 225, 203)),
    ]

    def paintSection(self, painter, rect, logical_index):
        # Linha 1: nome da coluna (altura normal)
        # Linha 2: nome do grupo com cor de fundo (altura extra 20px)
        ...
```

### Persistência do estado da faixa verde

O estado dos campos propostos (new_title, new_author, etc.) é mantido em memória durante a sessão.
Ao fechar o aplicativo, os campos propostos **não** são persistidos — a faixa verde é zerada a cada
sessão. O usuário deve aplicar ou exportar antes de fechar.

> Razão: persistir estado intermediário introduz complexidade de reconciliação se o arquivo em
> disco mudou entre sessões. Deferido para versão futura com timestamp de modificação.

## Open Questions

- [ ] O usuário quer poder reordenar as colunas dentro de cada faixa, ou a ordem é fixa?
- [ ] Queremos um modo "somente leitura" que oculta a faixa verde para inspeção rápida do acervo?
- [ ] A coluna separadora deve ser arrastável (para ajustar largura das faixas) ou fixa?
