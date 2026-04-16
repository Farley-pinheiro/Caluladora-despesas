# 📊 Controle de Dívidas

> Aplicação web para controle e acompanhamento de dívidas parceladas. Desenvolvida com arquitetura MVC, princípios SOLID e design Apple-inspired.

---

## 🚀 Tecnologias

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.10+ · Flask 3.x |
| Persistência | SQLite (via padrão Repository) |
| Frontend | HTML5 · Vanilla CSS · Vanilla JS |
| Testes | pytest · pytest-flask |
| Logging | JSON estruturado (custom formatter) |

---

## 🏗️ Arquitetura

```
src/
├── run.py                              # Entry point
├── config.py                           # Configurações por ambiente
├── requirements.txt
├── .env.example                        # Template de variáveis de ambiente
│
├── app/
│   ├── logger.py                       # Logger JSON estruturado
│   ├── app.py                          # Flask Factory + injeção de dependência
│   │
│   ├── models/
│   │   └── divida.py                   # Entidade de domínio (lógica pura)
│   │
│   ├── repositories/
│   │   ├── base_repository.py          # Interface abstrata (DIP)
│   │   ├── sqlite_divida_repository.py # Implementação SQLite
│   │   └── migrations.py              # Engine de migrações versionadas
│   │
│   ├── services/
│   │   └── divida_service.py           # Casos de uso e cálculos financeiros
│   │
│   ├── controllers/
│   │   └── divida_controller.py        # Blueprint Flask (rotas HTTP)
│   │
│   ├── views/templates/
│   │   ├── base.html                   # Layout base com navbar + modal
│   │   └── index.html                  # Dashboard principal
│   │
│   └── static/
│       ├── css/style.css               # Design system Apple-inspired
│       └── js/main.js                  # Fetch API + UX interactions
│
└── tests/
    ├── conftest.py                     # Fixtures (banco em memória)
    ├── test_model_divida.py            # 24 testes unitários do domínio
    ├── test_divida_service.py          # 12 testes unitários do service
    └── test_controller.py             # Testes de integração dos endpoints
```

---

## ⚙️ Instalação e Execução

### 1. Clone o repositório

```bash
git clone <url-do-repo>
cd Caluladora-despesas/src
```

### 2. Crie um ambiente virtual

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

```bash
cp .env.example .env
# Edite o .env com suas configurações
```

### 5. Execute a aplicação

```bash
python run.py
```

Acesse em: **http://127.0.0.1:5000**

---

## 🧪 Rodando os Testes

```bash
# Todos os testes
python -m pytest tests/ -v

# Com relatório de cobertura
python -m pytest tests/ -v --tb=short
```

**Resultado esperado:** 60+ testes passando em < 1 segundo.

---

## 🔌 API Endpoints

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/` | Dashboard principal (HTML) |
| `GET` | `/api/dividas` | Listar todas as dívidas |
| `POST` | `/api/dividas` | Criar nova dívida |
| `GET` | `/api/dividas/<id>` | Detalhar uma dívida |
| `PUT` | `/api/dividas/<id>/pagar` | Registrar pagamento de parcela |
| `DELETE` | `/api/dividas/<id>` | Excluir dívida |

### Exemplo de payload — Criar dívida

```json
POST /api/dividas
Content-Type: application/json

{
  "nome": "Cartão Nubank",
  "valor_total": 1200.00,
  "valor_parcela": 100.00,
  "total_parcelas": 12,
  "categoria": "Cartão de Crédito"
}
```

**Categorias disponíveis:** `Cartão de Crédito`, `Empréstimo`, `Financiamento`, `Aluguel`, `Saúde`, `Educação`, `Outro`

---

## 🏛️ Princípios SOLID Aplicados

| Princípio | Onde |
|---|---|
| **SRP** | Cada camada tem uma única responsabilidade: Model → domínio, Service → casos de uso, Controller → HTTP |
| **OCP** | `MIGRATIONS` em `migrations.py` — novas migrações são adicionadas sem alterar o engine |
| **LSP** | `SQLiteDividaRepository` substitui `BaseRepository` sem quebrar contratos |
| **ISP** | `BaseRepository` expõe apenas os métodos necessários para o domínio |
| **DIP** | `DividaService` depende de `BaseRepository` (abstração), não de `SQLiteDividaRepository` (concreto) |

---

## 🔒 Segurança

- **SQL Injection**: Todas as queries usam parâmetros parametrizados (`?`)
- **XSS**: `textContent` no JS (nunca `innerHTML` com dados do usuário)
- **CSRF**: Token de sessão validado em todas as requisições de mutação (POST/PUT/DELETE)
- **Validação**: Inputs validados em 3 camadas — JS (client), Controller (HTTP), Model (domínio)

---

## 🌍 Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `FLASK_ENV` | `development` | Ambiente de execução |
| `SECRET_KEY` | *(dev key)* | Chave secreta do Flask (obrigatória em produção) |
| `DB_PATH` | `controle_dividas.db` | Caminho do arquivo SQLite |
| `LOG_LEVEL` | `INFO` | Nível de logging (DEBUG, INFO, WARNING, ERROR) |
