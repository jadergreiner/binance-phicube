<script setup lang="ts">
/**
 * PositionTable — Tabela de posições abertas
 *
 * Exibe posições com ordenação por clique no header, filtro por símbolo,
 * e cores para PnL positivo/negativo.
 */
import { ref, computed } from 'vue';
import type { Position } from '@/services/types';
import SignalBadge from './SignalBadge.vue';
import LoadingSpinner from './LoadingSpinner.vue';

const props = defineProps<{
  positions: Position[];
  loading: boolean;
}>();

const emit = defineEmits<{
  sort: [column: string, direction: 'asc' | 'desc'];
}>();

const searchQuery = ref('');
const sortColumn = ref<string | null>(null);
const sortDirection = ref<'asc' | 'desc'>('asc');

const filteredPositions = computed(() => {
  let list = [...props.positions];

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase();
    list = list.filter((p) => p.symbol.toLowerCase().includes(q));
  }

  if (sortColumn.value) {
    list.sort((a, b) => {
      const aVal = a[sortColumn.value as keyof Position] as number | string;
      const bVal = b[sortColumn.value as keyof Position] as number | string;
      const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return sortDirection.value === 'asc' ? cmp : -cmp;
    });
  }

  return list;
});

function toggleSort(column: string) {
  if (sortColumn.value === column) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
  } else {
    sortColumn.value = column;
    sortDirection.value = 'asc';
  }
  emit('sort', column, sortDirection.value);
}

function sortIcon(column: string): string {
  if (sortColumn.value !== column) return '↕';
  return sortDirection.value === 'asc' ? '↑' : '↓';
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'USD',
  }).format(value);
}

function pnlClass(pnl: number): string {
  if (pnl > 0) return 'pnl-positive';
  if (pnl < 0) return 'pnl-negative';
  return '';
}
</script>

<template>
  <div class="position-table">
    <div class="position-table__toolbar">
      <input
        v-model="searchQuery"
        type="text"
        class="position-table__search"
        placeholder="Filtrar por símbolo..."
      />
    </div>

    <LoadingSpinner v-if="loading" />

    <div v-else-if="filteredPositions.length === 0" class="position-table__empty">
      Nenhuma posição aberta
    </div>

    <table v-else class="position-table__table">
      <thead>
        <tr>
          <th class="position-table__th clickable" @click="toggleSort('symbol')">
            Símbolo {{ sortIcon('symbol') }}
          </th>
          <th class="position-table__th">Direção</th>
          <th class="position-table__th clickable" @click="toggleSort('entry_price')">
            Entrada {{ sortIcon('entry_price') }}
          </th>
          <th class="position-table__th clickable" @click="toggleSort('current_price')">
            Atual {{ sortIcon('current_price') }}
          </th>
          <th class="position-table__th clickable" @click="toggleSort('quantity')">
            Qtd {{ sortIcon('quantity') }}
          </th>
          <th class="position-table__th clickable" @click="toggleSort('pnl_usdt')">
            P&L (USDT) {{ sortIcon('pnl_usdt') }}
          </th>
          <th class="position-table__th clickable" @click="toggleSort('pnl_pct')">
            P&L (%) {{ sortIcon('pnl_pct') }}
          </th>
          <th class="position-table__th">SL</th>
          <th class="position-table__th">TP</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="pos in filteredPositions" :key="pos.symbol">
          <td class="position-table__td position-table__td--symbol">{{ pos.symbol }}</td>
          <td class="position-table__td">
            <SignalBadge :direction="pos.direction" />
          </td>
          <td class="position-table__td">{{ formatCurrency(pos.entry_price) }}</td>
          <td class="position-table__td">{{ formatCurrency(pos.current_price) }}</td>
          <td class="position-table__td">{{ pos.quantity }}</td>
          <td class="position-table__td" :class="pnlClass(pos.pnl_usdt)">
            {{ formatCurrency(pos.pnl_usdt) }}
          </td>
          <td class="position-table__td" :class="pnlClass(pos.pnl_pct)">
            {{ pos.pnl_pct >= 0 ? '+' : '' }}{{ pos.pnl_pct.toFixed(2) }}%
          </td>
          <td class="position-table__td">{{ formatCurrency(pos.sl_price) }}</td>
          <td class="position-table__td">{{ formatCurrency(pos.tp_price) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.position-table {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.position-table__toolbar {
  padding: 16px;
  border-bottom: 1px solid var(--color-border);
}

.position-table__search {
  width: 100%;
  max-width: 300px;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.position-table__search:focus {
  border-color: var(--color-secondary);
}

.position-table__table {
  width: 100%;
  border-collapse: collapse;
}

.position-table__th {
  padding: 12px 16px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #fff;
  background: var(--color-primary);
  white-space: nowrap;
  user-select: none;
}

.position-table__th.clickable {
  cursor: pointer;
}

.position-table__th.clickable:hover {
  background: #34495e;
}

.position-table__td {
  padding: 12px 16px;
  font-size: 14px;
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border);
}

.position-table__td--symbol {
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

.pnl-positive {
  color: var(--color-success);
  font-weight: 600;
}

.pnl-negative {
  color: var(--color-danger);
  font-weight: 600;
}

.position-table__empty {
  padding: 48px;
  text-align: center;
  color: #999;
  font-size: 15px;
}
</style>
