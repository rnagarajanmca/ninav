export type ImageMetadata = {
  id: string
  name: string
  relative_path: string
  url: string
  size_bytes: number
  modified_at: string
}

export type ImageListResponse = {
  items: ImageMetadata[]
  page: number
  page_size: number
  total: number
}

export type ImageDeleteResponse = {
  original_path: string
  trashed_path: string
}

export type PersonItem = {
  id: string
  label: string
  face_count: number
  cover_face_id?: string | null
  cover_image_url?: string | null
}

export type PersonListResponse = {
  total: number
  items: PersonItem[]
}

export type FaceItem = {
  id: string
  image_id: string
  relative_path: string
  image_url: string
  confidence: number
  person_id?: string | null
}

export type FaceListResponse = {
  total: number
  limit: number
  offset: number
  items: FaceItem[]
}

export type FaceCluster = {
  cluster_id: number
  face_ids: string[]
  representative_face_id: string
  faces: FaceItem[]
}

export type FaceClusterResponse = {
  total_clusters: number
  clusters: FaceCluster[]
}
