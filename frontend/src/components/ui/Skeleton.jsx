// Skeletons de carga con efecto shimmer para evitar saltos de interfaz (CLS).

export function Skeleton({ className = '' }) {
  return (
    <div
      className={`animate-pulse rounded-md bg-slate-200/80 ${className}`}
      aria-hidden="true"
    />
  )
}

export function TableRowSkeleton() {
  return (
    <tr className="border-b border-slate-100 last:border-0">
      <td className="px-4 py-3">
        <Skeleton className="h-8 w-8 rounded-full" />
      </td>
      <td className="px-3 py-3">
        <div className="space-y-1.5">
          <Skeleton className="h-3.5 w-24" />
          <Skeleton className="h-4 w-12 rounded" />
        </div>
      </td>
      <td className="px-3 py-3">
        <div className="space-y-1.5">
          <Skeleton className="h-3.5 w-36" />
          <Skeleton className="h-3 w-20" />
        </div>
      </td>
      <td className="px-3 py-3">
        <div className="space-y-1.5">
          <Skeleton className="h-3.5 w-64" />
          <div className="flex gap-2">
            <Skeleton className="h-4 w-16 rounded" />
            <Skeleton className="h-4 w-20 rounded" />
          </div>
        </div>
      </td>
      <td className="px-3 py-3 text-right">
        <Skeleton className="ml-auto h-4 w-20" />
      </td>
      <td className="px-3 py-3">
        <Skeleton className="h-5 w-16 rounded-full" />
      </td>
      <td className="px-3 py-3">
        <div className="space-y-1">
          <Skeleton className="h-3.5 w-16" />
          <Skeleton className="h-3 w-12" />
        </div>
      </td>
      <td className="px-3 py-3 text-right">
        <Skeleton className="h-6 w-6 rounded" />
      </td>
    </tr>
  )
}

export function MobileCardSkeleton() {
  return (
    <div className="p-3.5 border-b border-slate-100 space-y-2.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Skeleton className="h-7 w-7 rounded-full" />
          <Skeleton className="h-3.5 w-24" />
          <Skeleton className="h-4 w-10 rounded" />
        </div>
        <Skeleton className="h-5 w-14 rounded-full" />
      </div>
      <div className="flex justify-between">
        <Skeleton className="h-3.5 w-32" />
        <Skeleton className="h-3 w-16" />
      </div>
      <Skeleton className="h-3.5 w-full" />
      <Skeleton className="h-3.5 w-4/5" />
      <div className="flex justify-between border-t border-slate-100 pt-2">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-16" />
      </div>
    </div>
  )
}

export function DetailSkeleton() {
  return (
    <div className="p-6 space-y-6 animate-pulse">
      <div className="space-y-3">
        <div className="flex gap-2">
          <Skeleton className="h-5 w-16 rounded" />
          <Skeleton className="h-5 w-28 rounded" />
          <Skeleton className="h-5 w-14 rounded-full" />
        </div>
        <Skeleton className="h-7 w-3/4 rounded-lg" />
        <Skeleton className="h-4 w-1/2" />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 border border-slate-100 rounded-xl bg-slate-50 space-y-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-5 w-24" />
        </div>
        <div className="p-3 border border-slate-100 rounded-xl bg-slate-50 space-y-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-5 w-20" />
        </div>
        <div className="p-3 border border-slate-100 rounded-xl bg-slate-50 space-y-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-5 w-24" />
        </div>
        <div className="p-3 border border-slate-100 rounded-xl bg-slate-50 space-y-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-5 w-20" />
        </div>
      </div>

      <div className="border border-slate-100 rounded-xl p-4 bg-slate-50 space-y-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-3.5 w-full" />
        <Skeleton className="h-3.5 w-5/6" />
      </div>
    </div>
  )
}
