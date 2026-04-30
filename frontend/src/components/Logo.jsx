/**
 * Logo RCA.
 * - text "RCA" en navy + el "." (punto) como bloque verde oliva
 * - sizes: sm | md | lg | xl
 * - variant: 'full' (RCA. + tagline) | 'compact' (solo RCA.)
 */
export default function Logo({ size = 'md', variant = 'compact', tagline = false, color = 'navy', className = '' }) {
  const sizes = {
    xs: { txt: 'text-base', dot: 'w-1.5 h-1.5 ml-[1px]', tag: 'text-[8px]' },
    sm: { txt: 'text-xl', dot: 'w-2 h-2 ml-0.5', tag: 'text-[9px]' },
    md: { txt: 'text-2xl', dot: 'w-2.5 h-2.5 ml-0.5', tag: 'text-[10px]' },
    lg: { txt: 'text-5xl', dot: 'w-4 h-4 ml-1', tag: 'text-xs' },
    xl: { txt: 'text-7xl', dot: 'w-6 h-6 ml-1.5', tag: 'text-sm' },
  }
  const s = sizes[size]
  const colors = {
    navy: 'text-navy',
    bone: 'text-bone',
    white: 'text-white',
  }

  return (
    <div className={`inline-flex flex-col leading-none ${className}`}>
      <div className={`flex items-end font-display font-bold tracking-tightest ${colors[color]} ${s.txt}`}>
        <span>RCA</span>
        <span className={`${s.dot} bg-olive rounded-[2px] mb-[0.15em]`} aria-hidden />
      </div>
      {tagline && (
        <div className={`${s.tag} font-medium tracking-[0.18em] uppercase mt-1.5 ${color === 'navy' ? 'text-olive-700' : 'text-olive-200'}`}>
          Diseño · Construcción · Servicio
        </div>
      )}
    </div>
  )
}
