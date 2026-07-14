# Visão geral da arquitetura

## Estilo arquitetural

A solução será um monólito modular em Django. Haverá uma única aplicação implantável e um único banco relacional, com separação interna por domínios.

```text
Navegador
├── interface do Usuário da Sala
├── painel do Estagiário
├── painel do Supervisor
└── seletor de perfil de teste
        │
        ▼
Django
├── templates e arquivos estáticos
├── API REST /api/v1/
├── serviços de domínio
├── consultas e projeções
└── autorização simulada
        │
        ▼
PostgreSQL
```

## Stack proposta

- Python;
- Django 5.2 LTS;
- Django REST Framework;
- PostgreSQL como banco-alvo;
- Django Templates;
- JavaScript puro para interações progressivas;
- `drf-spectacular` para OpenAPI;
- Docker Compose em etapa posterior de desenvolvimento e implantação.

## Motivação

O domínio possui transações fortemente relacionadas: reservas, sessões, alocações, estados de computador, ocorrências e relatórios. Um monólito modular reduz complexidade operacional e permite transações atômicas sem mensageria distribuída.

## Camadas internas

### Apresentação

Templates, JavaScript, views HTTP e serializers.

### Aplicação

Casos de uso implementados como serviços explícitos: reservar, iniciar sessão, trocar computador, encerrar sessão, corrigir registro e alterar estado operacional.

### Domínio

Modelos, regras, invariantes, enums e políticas de disponibilidade.

### Infraestrutura

ORM, PostgreSQL, exportadores, administração e futura auditoria.

## Princípios

- regras de negócio não devem depender do frontend;
- operações críticas devem ser transacionais;
- estados calculados não devem ser persistidos como fonte de verdade;
- relatórios consultam dados operacionais existentes;
- cada app Django possui responsabilidade clara;
- a API é versionada desde a primeira versão;
- a seleção de perfil é mecanismo de demonstração, não segurança.

## Limites atuais

- sem autenticação real;
- sem fila de espera;
- sem integração institucional;
- sem microsserviços;
- sem tarefas assíncronas;
- sem armazenamento de dados pessoais reais durante a fase de demonstração.
