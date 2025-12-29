import type { PersonItem } from '../types/media'
import { resolveMediaUrl } from '../lib/api'

interface PersonGridProps {
  persons: PersonItem[]
  loading: boolean
  error?: string
  selectedId: string | null
  onSelect: (id: string) => void
}

export function PersonGrid({ persons, loading, error, selectedId, onSelect }: PersonGridProps) {
  if (error) {
    return (
      <div className="person-grid">
        <div className="empty-state error">
          <p>{error}</p>
        </div>
      </div>
    )
  }

  if (loading && persons.length === 0) {
    return (
      <div className="person-grid">
        {Array.from({ length: 6 }, (_, index) => (
          <div key={index} className="person-card skeleton" />
        ))}
      </div>
    )
  }

  if (persons.length === 0) {
    return (
      <div className="person-grid">
        <div className="empty-state">
          <p>No people discovered yet.</p>
          <small>Scan faces or review assignments to populate this area.</small>
        </div>
      </div>
    )
  }

  return (
    <div className="person-grid">
      {persons.map((person) => {
        const coverSrc = person.cover_image_url ? resolveMediaUrl(person.cover_image_url) : null
        return (
          <button
            key={person.id}
            type="button"
            className={`person-card ${selectedId === person.id ? 'is-selected' : ''}`}
            onClick={() => onSelect(person.id)}
          >
            <div className="person-card__cover">
              {coverSrc ? (
                <img src={coverSrc} alt={`${person.label} cover`} loading="lazy" decoding="async" />
              ) : (
                <div className="person-card__placeholder">No cover</div>
              )}
            </div>
            <div className="person-card__meta">
              <strong>{person.label}</strong>
              <small>{person.face_count} face{person.face_count === 1 ? '' : 's'}</small>
            </div>
          </button>
        )
      })}
    </div>
  )
}
