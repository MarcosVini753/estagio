# ADR 0023: Adotar frontend progressivo com Django Templates, HTMX, Alpine.js e Tailwind CSS

## Status

Aceita.

## Contexto

O sistema é um monólito modular em Django e Django REST Framework. As regras críticas de disponibilidade, reservas, sessões, manutenção, calendário e relatórios pertencem ao backend e já são expostas por serviços e pela API `/api/`.

O protótipo navegável existente usa HTML, CSS e JavaScript puro e continua sendo uma referência visual. A aplicação não exige, nesta etapa, uma SPA separada nem um segundo ciclo de autenticação, roteamento, build e implantação.

A ADR 0004 estabelecia Django Templates e JavaScript puro. Essa direção continua válida no princípio de manter o frontend junto ao Django, mas precisa de uma estratégia mais clara para interações assíncronas, estado exclusivamente visual, estilos reutilizáveis e evolução mobile.

## Decisão

Adotar um frontend server-rendered e progressivamente aprimorado com:

- Django Templates como base de renderização e composição de páginas;
- HTMX para interações que exigem comunicação com o servidor e atualização parcial da interface;
- Alpine.js para estado local e efêmero de interface, como modais, menus, abas, filtros visuais e componentes semelhantes;
- Tailwind CSS 4 como base de estilos e construção do design system;
- JavaScript ou TypeScript apenas quando a interação não for adequadamente resolvida por HTML, HTMX ou Alpine.js;
- Chart.js para gráficos gerenciais quando as telas de relatórios e indicadores forem implementadas;
- abordagem mobile-first e preparada para evolução posterior para PWA.

A API `/api/` permanece como contrato executável do backend e pode ser consumida pelo frontend quando isso for mais adequado que respostas HTML parciais. A existência da API não implica separar o frontend em outro projeto.

O backend permanece a fonte de verdade. O frontend não deve reproduzir regras de disponibilidade, concorrência, autorização, reserva, duração de sessão ou transições de estado.

React, Vue, Angular, Next.js ou outro frontend SPA separado não serão introduzidos sem nova decisão arquitetural.

## Organização esperada

A implementação deve evoluir aproximadamente para:

```text
backend/
├── templates/
│   ├── base.html
│   ├── components/
│   ├── room_user/
│   ├── room_monitor/
│   └── supervisor/
└── static/
    ├── css/
    ├── js/
    ├── icons/
    └── images/
```

Componentes e partials devem ser reutilizados quando houver repetição real. Não criar uma camada própria de componentes ou estado global sem necessidade comprovada.

## Consequências positivas

- mantém uma única aplicação implantável;
- reduz complexidade de autenticação, CORS, roteamento e estado remoto;
- reaproveita sessões, CSRF e recursos nativos do Django;
- permite interfaces dinâmicas sem transformar o sistema em SPA;
- favorece progressive enhancement e acessibilidade;
- preserva a API para integrações futuras;
- permite migrar o protótipo gradualmente, sem reescrever regras de negócio no navegador.

## Consequências negativas e riscos

- HTMX e Alpine.js introduzem novas convenções que precisam ser documentadas;
- Tailwind CSS adiciona uma etapa de geração de CSS ao processo de frontend;
- TypeScript pode exigir bundler no futuro, mas não deve ser introduzido antes de existir necessidade concreta;
- partials HTML mal organizados podem gerar acoplamento entre views e templates;
- uma futura SPA exigiria nova avaliação arquitetural.

## Fora do escopo desta decisão

- implementar agora o frontend definitivo;
- transformar o sistema em PWA imediatamente;
- adicionar funcionamento offline;
- escolher detalhes finais de identidade visual;
- substituir a API REST por outra tecnologia.
