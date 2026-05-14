<script setup lang="ts">
/**
 * SignalBadge — Badge de direção de sinal
 *
 * Exibe LONG (azul), SHORT (vermelho) ou NEUTRO (cinza).
 */

interface SignalBadgeProps {
  direction: 'LONG' | 'SHORT' | 'NEUTRO';
}

defineProps<SignalBadgeProps>();
</script>

<template>
  <span class="signal-badge" :class="`signal-badge--${direction.toLowerCase()}`">
    {{ direction }}
  </span>
</template>

<style scoped>
.signal-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
  font-family: 'Courier New', Consolas, monospace;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  line-height: 1.4;
}

.signal-badge--long {
  background: rgba(52, 152, 219, 0.15);
  color: var(--color-secondary);
}

.signal-badge--short {
  background: rgba(231, 76, 60, 0.15);
  color: var(--color-danger);
}

.signal-badge--neutro {
  background: rgba(149, 165, 166, 0.15);
  color: #7f8c8d;
}
</style>
