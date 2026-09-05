# NFL Sideline

Um ecossistema analítico e plataforma cloud-native para predição quantitativa, ingestão de dados em lote da NFL e geração de relatórios táticos assistidos por RAG (Retrieval-Augmented Generation) com validação determinística anti-alucinação.

## 🏗️ Arquitetura do Sistema

O projeto adere estritamente aos princípios de Twelve-Factor App e Spec-Driven Development (SDD), desacoplando a ingestão de dados, o motor de inteligência e a interface visual.

```
[ nflverse Parquet ]
       │
       ▼ (ETL Polars/Python)
[ PostgreSQL / Supabase ] ◄─── (JPA / Hibernate EAGER)
       │
       ▼
[ Core API (Spring Boot 3 / Java 21) ]
       │
       ├─► [ SHA-256 Analysis Cache ]
       └─► [ Gemini 2.5 Flash Client ] ──► [ Validador Anti-Alucinação (Tolerância 0.01) ]
       │
       ▼
[ Web UI (React, Vite, TypeScript & Recharts) ]
```

## 🚀 Principais Módulos & Tecnologias

**Backend (`core-api/`):** Java 21, Spring Boot 3, Maven, Spring Data JPA / PostgreSQL, cliente HTTP nativo para integração com LLM.

**ETL Pipeline (`etl-pipeline/`):** Python 3.11+, Polars para processamento massivo de arquivos Parquet de play-by-play, psycopg2 e tipagem estrita.

**Frontend (`web-ui/`):** React 18, TypeScript, Vite, Recharts para visualização de assimetria de mercado e eficiência de passes/corridas, react-markdown para renderização de narrativas.

**Motor RAG & Confiabilidade:**

- Cache inteligente com hash SHA-256 do prompt para zerar latência e custo em consultas repetidas.
- Barreira determinística anti-alucinação comparando numéricas citadas contra o contexto com tolerância de 0.01 para arredondamentos do modelo.

## 📊 Pipeline de Dados e Métricas Avançadas

O pipeline processa o histórico completo de play-by-play e calendários da NFL, calculando métricas fundamentais para modelagem quantitativa:

- **EPA (Expected Points Added)** desagregado por tipo de jogada (`off_epa_pass`, `off_epa_rush`, `def_epa_pass`, `def_epa_rush`).
- **Success Rate** ofensivo e defensivo por semana e temporada.
- **Dropback Rate** para mensuração de tendências ofensivas e previsibilidade.
- **Precificação Implícita de Mercado:** Conversão de moneylines americanas em probabilidades brutas, remoção de overround (vig) e cálculo de fair value das odds.

## ⚙️ Configuração e Execução Local

### Pré-requisitos

- Java 21 e Maven 3.9+
- Node.js 18+ e npm
- Python 3.11+ com ambiente virtual configurado

### 1. Configuração de Ambiente (`.env`)

Crie um arquivo `.env` na raiz do repositório contendo as credenciais de acesso ao banco e à inteligência artificial:

```bash
SUPABASE_DB_URL=jdbc:postgresql://<seu-host>:5432/postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=sua_senha
GEMINI_API_KEY=sua_chave_gemini
```

### 2. Executando o Backend (Spring Boot)

```bash
cd core-api
export $(xargs < ../.env)
mvn clean package -DskipTests
java -jar target/core-api-0.1.0.jar
```

A API estará ativa em `http://localhost:8080`.

### 3. Executando o Frontend (React / Vite)

```bash
cd web-ui
npm install
npm run dev
```

A interface web estará acessível em `http://localhost:5173`.

## 🛡️ Contrato de Resiliência de IA (Anti-Alucinação)

Qualquer tentativa do modelo de inventar métricas numéricas fora do escopo determinístico do banco de dados aciona a barreira de validação. Caso haja divergência estrita acima da tolerância permitida, o endpoint degrada de forma graciosa retornando um erro RFC 7807 (503 Service Unavailable), garantindo que nenhum dado falso seja exibido ao usuário final.