# Guia de Desenvolvimento — Phicube Frontend

## Padrões de Componentização

### Props e Emits

- Todo componente deve ter props tipadas com `defineProps<T>()`
- Eventos devem ser tipados com `defineEmits<T>()`
- Usar nomes descritivos em português para props

```vue
<script setup lang="ts">
interface Props {
  label: string;
  value: number | string;
  delta?: number;
}
defineProps<Props>();
defineEmits<{ click: [] }>();
</script>
```

### Composição

- Preferir Composition API (`<script setup lang="ts">`)
- Extrair lógica repetida para `composables/`
- Usar `ref()` e `computed()` em vez de `data` e `computed`

## Como Estruturar uma Nova View

1. Criar arquivo em `src/views/NomeView.vue`
2. Adicionar rota em `src/router/index.ts` (lazy-loaded)
3. Adicionar link na Navbar
4. Usar store + polling para dados dinâmicos

## Como Usar Pinia Store

```typescript
// Definir store
export const useExemploStore = defineStore('exemplo', () => {
  const data = ref<Dado[]>([]);
  const loading = ref(false);
  async function fetchData() { /* ... */ }
  return { data, loading, fetchData };
});

// Em componente
const store = useExemploStore();
await store.fetchData();
```

## Como Adicionar uma Nova Rota

```typescript
// router/index.ts
{
  path: '/nova-rota',
  name: 'NovaRota',
  component: () => import('@/views/NovaRotaView.vue'),
}
```

## Testes

### Onde Colocar

- Testes de componente: `src/components/__tests__/Componente.spec.ts`
- Testes de store: `src/stores/__tests__/store.spec.ts`
- Testes de API: `src/services/__tests__/api.spec.ts`
- Testes de router: `src/router/__tests__/router.spec.ts`

### Como Estruturar

```typescript
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';

describe('MeuComponente', () => {
  it('renderiza corretamente', () => {
    const wrapper = mount(MeuComponente, { props: { /* ... */ } });
    expect(wrapper.text()).toContain('...');
  });
});
```

## TypeScript Strict: Regras

- `strict: true` no tsconfig
- Nunca usar `any` — prefira `unknown` se necessário
- Sempre tipar retorno de funções públicas
- Usar `interface` em vez de `type` para objetos (consistência)
- Exceções documentadas em comentários `// ts-expect-error` com justificativa

## Exemplo Prático: Adicionar UtilCard

1. Criar `src/components/UtilCard.vue` com props `util`, `value`
2. Importar e usar em `DashboardView.vue`
3. Opcional: adicionar teste em `src/components/__tests__/UtilCard.spec.ts`
4. Adicionar ao `index.ts` de exports se necessário
