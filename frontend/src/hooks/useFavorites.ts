import { useCallback, useEffect, useState } from 'react'

export function useFavorites() {
  const FAVORITES_STORAGE_KEY = 'ninav:favorites'
  const [favorites, setFavorites] = useState<Set<string>>(new Set())

  useEffect(() => {
    try {
      const stored = localStorage.getItem(FAVORITES_STORAGE_KEY)
      if (stored) {
        setFavorites(new Set(JSON.parse(stored)))
      }
    } catch {
      // Ignore localStorage errors
    }
  }, [])

  useEffect(() => {
    try {
      localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(Array.from(favorites)))
    } catch {
      // Ignore localStorage errors
    }
  }, [favorites])

  const toggleFavorite = useCallback((imageId: string) => {
    setFavorites((prev) => {
      const next = new Set(prev)
      if (next.has(imageId)) {
        next.delete(imageId)
      } else {
        next.add(imageId)
      }
      return next
    })
  }, [])

  const isFavorite = useCallback((imageId: string) => {
    return favorites.has(imageId)
  }, [favorites])

  const favoriteCount = favorites.size

  return {
    favorites,
    favoriteCount,
    toggleFavorite,
    isFavorite,
  }
}
