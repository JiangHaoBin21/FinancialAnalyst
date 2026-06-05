<template>
  <section class="glass-panel rounded-lg p-5">
    <div class="flex items-center justify-between gap-4">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-teal-200">
          Analyzing
        </p>
        <h2 class="mt-2 text-lg font-semibold text-white">多 Agent 正在协同分析</h2>
      </div>
      <div class="h-3 w-3 rounded-full bg-teal-300 shadow-[0_0_24px_rgba(45,212,191,0.95)]" />
    </div>

    <div class="mt-6 grid gap-3 sm:grid-cols-3">
      <div class="h-24 animate-pulse rounded-lg bg-white/[0.07]" />
      <div class="h-24 animate-pulse rounded-lg bg-white/[0.07]" />
      <div class="h-24 animate-pulse rounded-lg bg-white/[0.07]" />
    </div>

    <div class="mt-4 space-y-3">
      <div class="h-4 w-3/4 animate-pulse rounded bg-white/[0.08]" />
      <div class="h-4 w-5/6 animate-pulse rounded bg-white/[0.08]" />
      <div class="h-4 w-2/3 animate-pulse rounded bg-white/[0.08]" />
    </div>
  </section>
</template>
