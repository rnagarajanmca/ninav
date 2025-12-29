import { Bell, Search, Settings, UploadCloud } from 'lucide-react'

interface TopNavProps {
  onSettingsClick: () => void
}

export function TopNav({ onSettingsClick }: TopNavProps) {
  return (
    <header className="topbar">
      <div className="topbar__search">
        <Search size={18} aria-hidden />
        <input placeholder="Search people, albums, or places" />
      </div>

      <div className="topbar__actions">
        <button type="button" aria-label="Upload">
          <UploadCloud size={18} />
          Upload
        </button>
        <button type="button" aria-label="Notifications">
          <Bell size={18} />
        </button>
        <button type="button" aria-label="Settings" onClick={onSettingsClick}>
          <Settings size={18} />
        </button>
        <div className="avatar">NK</div>
      </div>
    </header>
  )
}
