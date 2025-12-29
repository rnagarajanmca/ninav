import type {
  FaceClusterResponse,
  FaceListResponse,
  ImageDeleteResponse,
  ImageListResponse,
  ImageMetadata,
  PersonListResponse,
} from '../types/media'

const DEFAULT_API_BASE = import.meta.env.DEV ? 'http://localhost:8000/api' : '/api'
const rawBase = import.meta.env.VITE_API_BASE?.trim()

const API_BASE = (rawBase && rawBase.length > 0 ? rawBase : DEFAULT_API_BASE).replace(/\/$/, '')

function getApiOrigin(): string {
  if (/^https?:\/\//.test(API_BASE)) {
    return new URL(API_BASE).origin
  }

  if (typeof window !== 'undefined') {
    return window.location.origin
  }

  return 'http://localhost'
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`)
  }

  return (await response.json()) as T
}

export async function fetchImages(params: { page?: number; page_size?: number } = {}) {
  const query = new URLSearchParams()
  if (params.page) query.set('page', String(params.page))
  if (params.page_size) query.set('page_size', String(params.page_size))
  const suffix = query.size ? `?${query.toString()}` : ''
  return request<ImageListResponse>(`/images${suffix}`)
}

/**
 * @deprecated This function loads ALL images into memory at once, which can cause
 * performance issues with large libraries (10k+ images). Consider implementing:
 * - Virtual scrolling (react-window, react-virtuoso)
 * - Infinite scroll with proper pagination
 * - Server-side filtering and search
 *
 * For now, this is acceptable for small to medium libraries (< 5000 images).
 */
export async function fetchAllImages(batchSize = 120): Promise<{ items: ImageMetadata[]; total: number }> {
  let page = 1
  let total = Infinity
  const items: ImageMetadata[] = []

  while (items.length < total) {
    const response = await fetchImages({ page, page_size: batchSize })
    items.push(...response.items)
    total = response.total
    if (response.items.length === 0) break
    page += 1
  }

  return { items, total: Number.isFinite(total) ? total : items.length }
}

export function resolveMediaUrl(path: string, thumbnail: boolean | 'small' | 'medium' | 'large' = false): string {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }

  const origin = getApiOrigin()
  const normalized = path.startsWith('/') ? path : `/${path}`

  // Use thumbnail endpoint if requested
  if (thumbnail) {
    const size = typeof thumbnail === 'string' ? thumbnail : 'medium'
    // Extract the path after /media/
    const mediaPath = normalized.replace('/media/', '')
    // URL encode each path segment to handle spaces and special characters
    const encodedPath = mediaPath.split('/').map(segment => encodeURIComponent(segment)).join('/')
    return `${origin}/thumbnails/${size}/${encodedPath}`
  }

  // URL encode the path for regular media URLs too
  const pathOnly = normalized.replace('/media/', '')
  const encodedPath = pathOnly.split('/').map(segment => encodeURIComponent(segment)).join('/')
  return `${origin}/media/${encodedPath}`
}

export const apiConfig = {
  baseUrl: API_BASE,
  get origin() {
    return getApiOrigin()
  },
}

export async function fetchPersons() {
  return request<PersonListResponse>('/persons')
}

export async function fetchFaces(params: { person_id?: string; limit?: number; offset?: number; status?: string } = {}) {
  const query = new URLSearchParams()
  if (params.person_id) query.set('person_id', params.person_id)
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (params.status) query.set('status', params.status)
  const suffix = query.size ? `?${query.toString()}` : ''
  return request<FaceListResponse>(`/faces${suffix}`)
}

export async function fetchFaceClusters(params: { threshold?: number; min_cluster_size?: number } = {}) {
  const query = new URLSearchParams()
  if (params.threshold !== undefined) query.set('threshold', String(params.threshold))
  if (params.min_cluster_size !== undefined) query.set('min_cluster_size', String(params.min_cluster_size))
  const suffix = query.size ? `?${query.toString()}` : ''
  return request<FaceClusterResponse>(`/faces/clusters${suffix}`)
}

export async function createPerson(label: string) {
  return request<PersonListResponse['items'][0]>('/persons', {
    method: 'POST',
    body: JSON.stringify({ label }),
  })
}

export async function assignFaces(personId: string, faceIds: string[]) {
  return request<{ count: number }>(`/persons/${personId}/assign`, {
    method: 'POST',
    body: JSON.stringify({ face_ids: faceIds }),
  })
}

export async function unassignFaces(personId: string, faceIds: string[]) {
  return request<{ count: number }>(`/persons/${personId}/unassign`, {
    method: 'POST',
    body: JSON.stringify({ face_ids: faceIds }),
  })
}

export async function renamePerson(personId: string, label: string) {
  return request<PersonListResponse['items'][0]>(`/persons/${personId}`, {
    method: 'PATCH',
    body: JSON.stringify({ label }),
  })
}

export async function deletePerson(personId: string) {
  return request<void>(`/persons/${personId}`, {
    method: 'DELETE',
  })
}

export async function mergePersons(targetPersonId: string, sourcePersonIds: string[]) {
  return request<PersonListResponse['items'][0]>(`/persons/${targetPersonId}/merge`, {
    method: 'POST',
    body: JSON.stringify({ source_person_ids: sourcePersonIds }),
  })
}

export async function renameImage(relativePath: string, newName: string) {
  return request<ImageMetadata>('/images/rename', {
    method: 'POST',
    body: JSON.stringify({ relative_path: relativePath, new_name: newName }),
  })
}

export async function deleteImage(relativePath: string) {
  return request<ImageDeleteResponse>('/images/delete', {
    method: 'POST',
    body: JSON.stringify({ relative_path: relativePath }),
  })
}

export function getFolderFromPath(relativePath: string | undefined): string {
  if (!relativePath) return ''
  const index = relativePath.lastIndexOf('/')
  if (index === -1) return ''
  return relativePath.slice(0, index)
}

export function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes)) {
    return '--'
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unitIndex]}`
}

export async function fetchStorageStats() {
  return request<{
    total_bytes: number
    total_gb: number
    image_count: number
    media_path: string
  }>('/storage')
}

export async function getScanStatus() {
  return request<{
    is_running: boolean
    total_images: number
    processed_images: number
    current_image: string | null
    started_at: string | null
    progress_percent: number
  }>('/scan/status')
}

export async function controlScan(action: 'start' | 'stop') {
  return request<{ status: string; message: string }>('/scan/control', {
    method: 'POST',
    body: JSON.stringify({ action }),
  })
}

export async function getSyncStatus() {
  return request<{
    is_running: boolean
    last_report: {
      scanned: number
      inserted: number
      updated: number
      removed: number
    } | null
  }>('/scan/sync-status')
}

export async function syncMedia() {
  return request<{
    status: string
    message: string
  }>('/scan/sync-media', {
    method: 'POST',
  })
}
