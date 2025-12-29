import { useEffect, useState } from 'react'
import { X, Play, Square, Loader2 } from 'lucide-react'
import { getScanStatus, controlScan } from '../lib/api'

interface ScanStatus {
  is_running: boolean
  total_images: number
  processed_images: number
  current_image: string | null
  started_at: string | null
  progress_percent: number
  is_syncing?: boolean
}

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [scanStatus, setScanStatus] = useState<ScanStatus>({
    is_running: false,
    total_images: 0,
    processed_images: 0,
    current_image: null,
    started_at: null,
    progress_percent: 0,
  })
  const [isLoading, setIsLoading] = useState(false)

  // Poll scan status when modal is open
  useEffect(() => {
    if (!isOpen) return

    const fetchStatus = async () => {
      try {
        const status = await getScanStatus()
        setScanStatus(status)
      } catch (error) {
        console.error('Failed to fetch scan status:', error)
      }
    }

    fetchStatus()
    const interval = setInterval(fetchStatus, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
  }, [isOpen])

  const handleStartScan = async () => {
    setIsLoading(true)
    try {
      await controlScan('start')
      // Fetch updated status
      const status = await getScanStatus()
      setScanStatus(status)
    } catch (error: any) {
      alert(error.message || 'Failed to start scan')
    } finally {
      setIsLoading(false)
    }
  }

  const handleStopScan = async () => {
    setIsLoading(true)
    try {
      await controlScan('stop')
      // Fetch updated status
      const status = await getScanStatus()
      setScanStatus(status)
    } catch (error: any) {
      alert(error.message || 'Failed to stop scan')
    } finally {
      setIsLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Settings</h2>
          <button type="button" onClick={onClose} className="modal-close" aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {/* Face Scanning Section */}
          <section className="settings-section">
            <h3>Face Detection</h3>
            <p className="settings-description">
              Scan your photos to detect and recognize faces. The media directory will be
              automatically synced before scanning to ensure all images are up to date.
            </p>

            <div className="scan-controls">
              <div className="scan-status">
                {scanStatus.is_running ? (
                  <>
                    <div className="status-indicator status-running">
                      <Loader2 size={16} className="spin" />
                      <span>{scanStatus.is_syncing ? 'Syncing...' : 'Scanning...'}</span>
                    </div>
                    <div className="scan-progress">
                      {scanStatus.is_syncing ? (
                        <div className="progress-text">
                          Syncing media directory with database...
                        </div>
                      ) : (
                        <>
                          <div className="progress-bar">
                            <div
                              className="progress-fill"
                              style={{ width: `${scanStatus.progress_percent}%` }}
                            />
                          </div>
                          <div className="progress-text">
                            {scanStatus.processed_images} / {scanStatus.total_images} images
                            ({Math.round(scanStatus.progress_percent)}%)
                          </div>
                          {scanStatus.current_image && (
                            <div className="current-image">
                              Processing: {scanStatus.current_image}
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="status-indicator status-idle">
                    <span>Idle</span>
                  </div>
                )}
              </div>

              <div className="scan-buttons">
                {scanStatus.is_running ? (
                  <button
                    type="button"
                    onClick={handleStopScan}
                    disabled={isLoading}
                    className="button button-secondary"
                  >
                    <Square size={16} />
                    Stop Scanning
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleStartScan}
                    disabled={isLoading}
                    className="button button-primary"
                  >
                    <Play size={16} />
                    Start Scanning
                  </button>
                )}
              </div>

              {scanStatus.processed_images > 0 && !scanStatus.is_running && (
                <div className="scan-summary">
                  Last scan: Processed {scanStatus.processed_images} images
                </div>
              )}
            </div>
          </section>

          {/* Future Settings Sections */}
          <section className="settings-section">
            <h3>Storage</h3>
            <p className="settings-description">
              Configure storage and caching options for your photo library.
            </p>
            <div className="settings-item">
              <label>
                <input type="checkbox" defaultChecked />
                <span>Enable thumbnail caching</span>
              </label>
            </div>
          </section>
        </div>

        <div className="modal-footer">
          <button type="button" onClick={onClose} className="button button-secondary">
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
