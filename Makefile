# ============================================================
# Mentor de Carreira — atalhos de desenvolvimento
# Requer GNU Make. No Windows, use Git Bash ou WSL.
# ============================================================

# Detecta o Python do ambiente virtual, se existir
VENV_PY  := venv/Scripts/python
VENV_PIP := venv/Scripts/pip

ifeq ($(shell test -f venv/bin/python && echo yes),yes)
	VENV_PY  := venv/bin/python
	VENV_PIP := venv/bin/pip
endif

PYTHON   ?= $(VENV_PY)
PIP      ?= $(VENV_PIP)

.PHONY: help install run test coverage lint clean diagrams

help:               ## Mostra esta mensagem de ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ------------------------------------------------------------
# Instalação
# ------------------------------------------------------------

install:            ## Cria o venv e instala todas as dependências (dev)
	python -m venv venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

# ------------------------------------------------------------
# Execução
# ------------------------------------------------------------

run:                ## Sobe o servidor em modo desenvolvimento (hot-reload)
	$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ------------------------------------------------------------
# Testes
# ------------------------------------------------------------

test:               ## Executa toda a suite de testes com saída detalhada
	$(PYTHON) -m pytest tests/ -v --tb=short

test-fast:          ## Executa os testes sem verbose (mais rápido)
	$(PYTHON) -m pytest tests/ -q

coverage:           ## Executa os testes e gera relatório de cobertura HTML
	$(PYTHON) -m pytest tests/ --cov=app --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "Relatório HTML gerado em: htmlcov/index.html"

# ------------------------------------------------------------
# Qualidade de código
# ------------------------------------------------------------

lint:               ## Verifica formatação e erros com ruff
	$(PYTHON) -m ruff check app/ tests/

format:             ## Formata o código automaticamente com ruff
	$(PYTHON) -m ruff format app/ tests/

# ------------------------------------------------------------
# Diagramas
# ------------------------------------------------------------

diagrams:           ## Renderiza os diagramas Mermaid (diagramas/*.mmd) em PNG e SVG
	@for f in diagramas/*.mmd; do \
		base=$${f%.mmd}; \
		echo "Renderizando $$base (.png + .svg)"; \
		npx -y @mermaid-js/mermaid-cli -i "$$f" -o "$$base.png" -b white -s 2; \
		npx -y @mermaid-js/mermaid-cli -i "$$f" -o "$$base.svg" -b white; \
	done

# ------------------------------------------------------------
# Limpeza
# ------------------------------------------------------------

clean:              ## Remove caches, .pyc e arquivos gerados
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	@echo "Caches removidos."
