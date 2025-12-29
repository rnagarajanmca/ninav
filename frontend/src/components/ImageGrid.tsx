import { memo } from 'react'
import type { ImageMetadata } from '../types/media'
import { resolveMediaUrl } from '../lib/api'

interface ImageGridProps {
  images: ImageMetadata[]
  loading?: boolean
  error?: string
  onSelect?: (image: ImageMetadata) => void
  favoriteIds?: Set<string>
  onToggleFavorite?: (image: ImageMetadata) => void
}

export const ImageGrid = memo(function ImageGrid({
  images,
  loading,
  error,
  onSelect,
  favoriteIds,
  onToggleFavorite,
}: ImageGridProps) {
  if (error) {
    return (
      <div className="empty-state error">
        <p>Unable to load images.</p>
        <small>{error}</small>
      </div>
    )
  }

  if (loading && images.length === 0) {
    return (
      <div className="grid grid--skeleton">
        {Array.from({ length: 24 }, (_, index) => (
          <div className="skeleton" key={index} />
        ))}
      </div>
    )
  }

  if (!loading && images.length === 0) {
    return (
      <div className="empty-state">
        <p>No media discovered yet.</p>
        <small>Drop images into the shared folder and hit refresh.</small>
      </div>
    )
  }

  return (
    <div className="grid">
      {images.map((image) => {
        const isFavorite = favoriteIds?.has(image.id)
        return (
          <button
            key={image.id}
            type="button"
            className={`grid__item grid__item--interactive ${isFavorite ? 'is-favorite' : ''}`}
            onClick={() => onSelect?.(image)}
          >
            <img
              src={resolveMediaUrl(image.url, 'small')}
              srcSet={`${resolveMediaUrl(image.url, 'small')} 300w, ${resolveMediaUrl(image.url, 'medium')} 800w`}
              sizes="(max-width: 600px) 300px, 400px"
              alt={image.name}
              loading="lazy"
              decoding="async"
              onError={(event) => {
                event.currentTarget.classList.add('is-broken')
              }}
            />
            <figcaption>
              <span>{image.name}</span>
              <small>{new Date(image.modified_at).toLocaleDateString()}</small>
            </figcaption>
            {onToggleFavorite && (
              <span
                className={`grid__favorite ${isFavorite ? 'is-active' : ''}`}
                role="button"
                aria-label={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
                aria-pressed={isFavorite}
                onClick={(event) => {
                  event.stopPropagation()
                  onToggleFavorite(image)
                }}
              >
                {isFavorite ? '❤️' : '🤍'}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
})
