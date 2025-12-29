import { useEffect, useState } from 'react'
import type { LucideIcon } from 'lucide-react'
import {
  Album,
  Clock3,
  Heart,
  Image as ImageIcon,
  LayoutGrid,
  MonitorPlay,
  Sparkles,
  UsersRound,
} from 'lucide-react'
import { fetchStorageStats, formatFileSize } from '../lib/api'

const sections: SidebarSection[] = [
  {
    title: 'Library',
    items: [
      { label: 'All Photos', key: 'all', icon: LayoutGrid },
      { label: 'Timeline', key: 'timeline', icon: Clock3 },
      { label: 'Faces', key: 'faces', icon: UsersRound },
      { label: 'Memories', key: 'memories', icon: Sparkles },
    ],
  },
  {
    title: 'Albums',
    items: [
      { label: 'Custom Albums', key: 'albums', icon: Album },
      { label: 'Favorites', key: 'favorites', icon: Heart },
      { label: 'Videos', key: 'videos', icon: MonitorPlay },
      { label: 'Imports', key: 'imports', icon: ImageIcon },
    ],
  },
]

type SidebarSection = {
  title: string
  items: { label: string; key: string; icon: LucideIcon }[]
}

interface SidebarNavProps {
  activeItem: string
  onSelect: (key: string) => void
  counts?: {
    all?: number
    favorites?: number
    faces?: number
    videos?: number
  }
}

export function SidebarNav({ activeItem, onSelect, counts }: SidebarNavProps) {
  const [storageStats, setStorageStats] = useState<{
    total_bytes: number
    total_gb: number
    image_count: number
  } | null>(null)

  useEffect(() => {
    fetchStorageStats()
      .then(setStorageStats)
      .catch(() => {
        // Ignore errors, keep showing placeholder
      })
  }, [])

  const storagePercentage = storageStats ? Math.min((storageStats.total_gb / 500) * 100, 100) : 62
  const storageText = storageStats
    ? `${formatFileSize(storageStats.total_bytes)} of 500 GB`
    : '312 GB of 500 GB'

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__logo">Ninav</div>
        <p className="sidebar__subtitle">AI-Powered Photo Browser</p>
      </div>

      {sections.map((section) => (
        <div key={section.title} className="sidebar__section">
          <p className="sidebar__section-title">{section.title}</p>
          <ul className="sidebar__list">
            {section.items.map((item) => {
              const isActive = item.key === activeItem
              const count = counts?.[item.key as keyof typeof counts]
              return (
                <li key={item.key} className={isActive ? 'is-active' : ''}>
                  <button
                    type="button"
                    onClick={() => onSelect(item.key)}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <item.icon size={18} aria-hidden />
                    <span>{item.label}</span>
                    {count !== undefined && count > 0 && (
                      <span className="sidebar__badge">{count}</span>
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      ))}

      <div className="sidebar__status">
        <p>Storage overview</p>
        <div className="status-bar">
          <span style={{ width: `${storagePercentage}%` }} />
        </div>
        <small>{storageText}</small>
      </div>
    </aside>
  )
}
