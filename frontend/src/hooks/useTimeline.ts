import { useMemo } from 'react'
import type { ImageMetadata } from '../types/media'

export interface TimelineGroup {
  key: string
  date: Date
  label: string
  dayLabel: string
  monthLabel: string
  yearLabel: string
  images: ImageMetadata[]
  count: number
  isNewMonth: boolean
  isNewYear: boolean
}

export function useTimeline(images: ImageMetadata[]) {
  const timelineGroups = useMemo(() => {
    // Group by day
    const groups = new Map<string, ImageMetadata[]>()
    images.forEach((image) => {
      const date = new Date(image.modified_at)
      const dayKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
      if (!groups.has(dayKey)) groups.set(dayKey, [])
      groups.get(dayKey)!.push(image)
    })

    // Sort and create timeline groups with metadata
    const sortedGroups = Array.from(groups.entries())
      .map(([key, images]) => {
        const date = new Date(key)
        const now = new Date()
        const yesterday = new Date(now)
        yesterday.setDate(yesterday.getDate() - 1)

        // Create labels
        const isToday = date.toDateString() === now.toDateString()
        const isYesterday = date.toDateString() === yesterday.toDateString()

        let dayLabel: string
        if (isToday) {
          dayLabel = 'Today'
        } else if (isYesterday) {
          dayLabel = 'Yesterday'
        } else {
          dayLabel = date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })
        }

        return {
          key,
          date,
          label: dayLabel,
          dayLabel: date.getDate().toString(),
          monthLabel: date.toLocaleDateString('en-US', { month: 'short' }),
          yearLabel: date.getFullYear().toString(),
          images,
          count: images.length,
          isNewMonth: false,
          isNewYear: false,
        }
      })
      .sort((a, b) => b.date.getTime() - a.date.getTime())

    // Mark new months and years
    for (let i = 0; i < sortedGroups.length; i++) {
      const current = sortedGroups[i]
      const previous = sortedGroups[i - 1]

      if (!previous || current.date.getFullYear() !== previous.date.getFullYear()) {
        current.isNewYear = true
        current.isNewMonth = true
      } else if (current.date.getMonth() !== previous.date.getMonth()) {
        current.isNewMonth = true
      }
    }

    return sortedGroups
  }, [images])

  // Create month groups for navigator
  const monthGroups = useMemo(() => {
    const groups = new Map<string, number>()
    timelineGroups.forEach((group) => {
      const monthKey = `${group.date.getFullYear()}-${String(group.date.getMonth() + 1).padStart(2, '0')}`
      groups.set(monthKey, (groups.get(monthKey) || 0) + group.count)
    })

    return Array.from(groups.entries())
      .map(([key, count]) => ({
        key,
        label: new Date(key + '-01').toLocaleDateString('en-US', { year: 'numeric', month: 'long' }),
        count,
      }))
      .sort((a, b) => b.key.localeCompare(a.key))
  }, [timelineGroups])

  return { timelineGroups, monthGroups }
}
