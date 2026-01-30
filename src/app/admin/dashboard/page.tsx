"use client"

import { useState, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  LayoutDashboard,
  FileText,
  Palette,
  Menu,
  Cpu,
  MemoryStick,
  Container,
  Activity,
  Save,
  Plus,
  Trash2,
  GripVertical,
  Eye,
  EyeOff,
  Check,
  RefreshCw,
  AlertCircle,
} from "lucide-react"
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import ReactMde from "react-mde"
import * as Showdown from "showdown"
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core"
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from "recharts"
import { ThemeEditor } from "@/components/admin/ThemeEditor"

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// ============== Types ==============

interface SystemStats {
  cpu: {
    percent: number
    count: number
    freq_current: number
  }
  memory: {
    percent: number
    used_gb: number
    total_gb: number
    available_gb: number
  }
  containers: {
    total: number
    running: number
    stopped: number
  }
  timestamp: string
}

interface StaticPage {
  id: string
  slug: string
  title: string
  content_markdown: string
  meta_description: string | null
  is_published: boolean
  created_at: string
  updated_at: string
}

interface NavItem {
  id: string
  label: string
  url: string
  order_index: number
  is_visible: boolean
  icon: string | null
}

type TabType = "overview" | "cms" | "theme" | "navigation"

// ============== Components ==============

function GaugeChart({
  value,
  max,
  label,
  color,
  icon: Icon,
}: {
  value: number
  max: number
  label: string
  color: string
  icon: React.ElementType
}) {
  const percentage = Math.min((value / max) * 100, 100)
  const data = [
    { name: "used", value: percentage },
    { name: "free", value: 100 - percentage },
  ]

  return (
    <div className="flex flex-col items-center p-4 bg-card border border-border rounded-xl">
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-4 h-4 text-muted-foreground" />
        <span className="text-sm font-medium text-foreground">{label}</span>
      </div>
      <div className="relative w-32 h-32">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={35}
              outerRadius={50}
              startAngle={90}
              endAngle={-270}
              dataKey="value"
              stroke="none"
            >
              <Cell fill={color} />
              <Cell fill="hsl(var(--muted))" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold text-foreground">
            {Math.round(percentage)}%
          </span>
        </div>
      </div>
      <p className="text-xs text-muted-foreground mt-2">
        {value.toFixed(1)} / {max.toFixed(1)}
      </p>
    </div>
  )
}

function StatsPanel() {
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch("/api/admin/stats")
      if (!response.ok) throw new Error("Failed to fetch stats")
      const data = await response.json()
      setStats(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch stats")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 5000)
    return () => clearInterval(interval)
  }, [fetchStats])

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-48 bg-card border border-border rounded-xl animate-pulse"
          />
        ))}
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="p-8 text-center bg-card border border-border rounded-xl">
        <AlertCircle className="w-8 h-8 text-destructive mx-auto mb-2" />
        <p className="text-muted-foreground">{error || "No stats available"}</p>
        <button
          onClick={fetchStats}
          className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary" />
          System Statistics
        </h3>
        <button
          onClick={fetchStats}
          className="p-2 text-muted-foreground hover:text-foreground rounded-lg hover:bg-muted transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <GaugeChart
          value={stats.cpu.percent}
          max={100}
          label="CPU Usage"
          color="hsl(var(--primary))"
          icon={Cpu}
        />
        <GaugeChart
          value={stats.memory.used_gb}
          max={stats.memory.total_gb}
          label="Memory Usage"
          color="hsl(142, 76%, 36%)"
          icon={MemoryStick}
        />
        <GaugeChart
          value={stats.containers.running}
          max={Math.max(stats.containers.total, 1)}
          label="Containers"
          color="hsl(217, 91%, 60%)"
          icon={Container}
        />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 bg-card border border-border rounded-lg">
          <p className="text-xs text-muted-foreground">CPU Cores</p>
          <p className="text-2xl font-bold text-foreground">{stats.cpu.count}</p>
        </div>
        <div className="p-4 bg-card border border-border rounded-lg">
          <p className="text-xs text-muted-foreground">Memory Total</p>
          <p className="text-2xl font-bold text-foreground">
            {stats.memory.total_gb.toFixed(1)} GB
          </p>
        </div>
        <div className="p-4 bg-card border border-border rounded-lg">
          <p className="text-xs text-muted-foreground">Containers Running</p>
          <p className="text-2xl font-bold text-green-500">{stats.containers.running}</p>
        </div>
        <div className="p-4 bg-card border border-border rounded-lg">
          <p className="text-xs text-muted-foreground">Containers Stopped</p>
          <p className="text-2xl font-bold text-muted-foreground">
            {stats.containers.stopped}
          </p>
        </div>
      </div>
    </div>
  )
}

// ============== CMS Editor ==============

const converter = new Showdown.Converter({
  tables: true,
  simplifiedAutoLink: true,
  strikethrough: true,
  tasklists: true,
})

function CmsEditor() {
  const [pages, setPages] = useState<StaticPage[]>([])
  const [selectedPage, setSelectedPage] = useState<StaticPage | null>(null)
  const [markdown, setMarkdown] = useState("")
  const [selectedTab, setSelectedTab] = useState<"write" | "preview">("write")
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const fetchPages = useCallback(async () => {
    try {
      const response = await fetch("/api/admin/pages")
      if (!response.ok) throw new Error("Failed to fetch pages")
      const data = await response.json()
      setPages(data.pages)
    } catch (err) {
      console.error("Failed to fetch pages:", err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPages()
  }, [fetchPages])

  const handleSave = async () => {
    if (!selectedPage) return
    setSaving(true)
    try {
      const response = await fetch(`/api/admin/pages/${selectedPage.slug}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content_markdown: markdown,
        }),
      })
      if (!response.ok) throw new Error("Failed to save")
      await fetchPages()
    } catch (err) {
      console.error("Failed to save page:", err)
    } finally {
      setSaving(false)
    }
  }

  const handleCreate = async () => {
    const slug = prompt("Enter page slug (lowercase, hyphens only):")
    if (!slug) return
    const title = prompt("Enter page title:")
    if (!title) return

    try {
      const response = await fetch("/api/admin/pages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slug,
          title,
          content_markdown: "# " + title + "\n\nStart writing here...",
          is_published: false,
        }),
      })
      if (!response.ok) throw new Error("Failed to create")
      await fetchPages()
    } catch (err) {
      console.error("Failed to create page:", err)
    }
  }

  const handleDelete = async (slug: string) => {
    if (!confirm("Are you sure you want to delete this page?")) return
    try {
      const response = await fetch(`/api/admin/pages/${slug}`, {
        method: "DELETE",
      })
      if (!response.ok) throw new Error("Failed to delete")
      if (selectedPage?.slug === slug) {
        setSelectedPage(null)
        setMarkdown("")
      }
      await fetchPages()
    } catch (err) {
      console.error("Failed to delete page:", err)
    }
  }

  if (loading) {
    return (
      <div className="h-96 flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
          <FileText className="w-5 h-5 text-primary" />
          CMS Editor
        </h3>
        <button
          onClick={handleCreate}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
        >
          <Plus className="w-4 h-4" />
          New Page
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Pages List */}
        <div className="lg:col-span-1 space-y-2">
          {pages.map((page) => (
            <div
              key={page.id}
              onClick={() => {
                setSelectedPage(page)
                setMarkdown(page.content_markdown)
              }}
              className={cn(
                "p-3 rounded-lg border cursor-pointer transition-colors",
                selectedPage?.id === page.id
                  ? "bg-primary/10 border-primary"
                  : "bg-card border-border hover:border-primary/50"
              )}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-foreground">{page.title}</span>
                {page.is_published ? (
                  <Eye className="w-4 h-4 text-green-500" />
                ) : (
                  <EyeOff className="w-4 h-4 text-muted-foreground" />
                )}
              </div>
              <p className="text-xs text-muted-foreground">/{page.slug}</p>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleDelete(page.slug)
                }}
                className="mt-2 text-xs text-destructive hover:underline"
              >
                Delete
              </button>
            </div>
          ))}
        </div>

        {/* Editor */}
        <div className="lg:col-span-3">
          {selectedPage ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-foreground">{selectedPage.title}</h4>
                  <p className="text-sm text-muted-foreground">/{selectedPage.slug}</p>
                </div>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50"
                >
                  {saving ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  Save
                </button>
              </div>
              <div className="border border-border rounded-lg overflow-hidden">
                <ReactMde
                  value={markdown}
                  onChange={setMarkdown}
                  selectedTab={selectedTab}
                  onTabChange={setSelectedTab}
                  generateMarkdownPreview={(markdown) =>
                    Promise.resolve(converter.makeHtml(markdown))
                  }
                  classes={{
                    toolbar: "bg-muted border-b border-border",
                    preview: "bg-card p-4",
                    textArea: "bg-background text-foreground",
                  }}
                />
              </div>
            </div>
          ) : (
            <div className="h-96 flex items-center justify-center bg-card border border-border rounded-lg">
              <p className="text-muted-foreground">Select a page to edit</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ============== Nav Editor ==============

function SortableNavItem({
  item,
  onToggle,
  onDelete,
}: {
  item: NavItem
  onToggle: (id: string) => void
  onDelete: (id: string) => void
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "flex items-center gap-3 p-3 bg-card border border-border rounded-lg",
        !item.is_visible && "opacity-50"
      )}
    >
      <button
        {...attributes}
        {...listeners}
        className="p-1 text-muted-foreground hover:text-foreground cursor-grab active:cursor-grabbing"
      >
        <GripVertical className="w-4 h-4" />
      </button>
      <div className="flex-1">
        <p className="font-medium text-foreground">{item.label}</p>
        <p className="text-xs text-muted-foreground">{item.url}</p>
      </div>
      <button
        onClick={() => onToggle(item.id)}
        className={cn(
          "p-2 rounded-lg transition-colors",
          item.is_visible
            ? "text-green-500 hover:bg-green-500/10"
            : "text-muted-foreground hover:bg-muted"
        )}
      >
        {item.is_visible ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
      </button>
      <button
        onClick={() => onDelete(item.id)}
        className="p-2 text-destructive hover:bg-destructive/10 rounded-lg transition-colors"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  )
}

function NavEditor() {
  const [items, setItems] = useState<NavItem[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [newItem, setNewItem] = useState({ label: "", url: "" })

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const fetchItems = useCallback(async () => {
    try {
      const response = await fetch("/api/public/config")
      if (!response.ok) throw new Error("Failed to fetch navigation")
      const data = await response.json()
      setItems(data.navigation || [])
    } catch (err) {
      console.error("Failed to fetch navigation:", err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchItems()
  }, [fetchItems])

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (over && active.id !== over.id) {
      setItems((items) => {
        const oldIndex = items.findIndex((item) => item.id === active.id)
        const newIndex = items.findIndex((item) => item.id === over.id)
        return arrayMove(items, oldIndex, newIndex)
      })
    }
  }

  const handleToggle = (id: string) => {
    setItems((items) =>
      items.map((item) =>
        item.id === id ? { ...item, is_visible: !item.is_visible } : item
      )
    )
  }

  const handleDelete = (id: string) => {
    setItems((items) => items.filter((item) => item.id !== id))
  }

  const handleAdd = () => {
    if (!newItem.label || !newItem.url) return
    const item: NavItem = {
      id: `temp-${Date.now()}`,
      label: newItem.label,
      url: newItem.url,
      order_index: items.length,
      is_visible: true,
      icon: null,
    }
    setItems([...items, item])
    setNewItem({ label: "", url: "" })
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const response = await fetch("/api/admin/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          navigation: items.map((item, index) => ({
            ...item,
            order_index: index,
          })),
        }),
      })
      if (!response.ok) throw new Error("Failed to save")
      await fetchItems()
    } catch (err) {
      console.error("Failed to save navigation:", err)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="h-96 flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
          <Menu className="w-5 h-5 text-primary" />
          Navigation Editor
        </h3>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50"
        >
          {saving ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          Save Order
        </button>
      </div>

      {/* Add New Item */}
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Label"
          value={newItem.label}
          onChange={(e) => setNewItem({ ...newItem, label: e.target.value })}
          className="flex-1 px-3 py-2 bg-background border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <input
          type="text"
          placeholder="URL"
          value={newItem.url}
          onChange={(e) => setNewItem({ ...newItem, url: e.target.value })}
          className="flex-1 px-3 py-2 bg-background border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <button
          onClick={handleAdd}
          disabled={!newItem.label || !newItem.url}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* Sortable List */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={items.map((i) => i.id)} strategy={verticalListSortingStrategy}>
          <div className="space-y-2">
            {items.map((item) => (
              <SortableNavItem
                key={item.id}
                item={item}
                onToggle={handleToggle}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {items.length === 0 && (
        <div className="p-8 text-center bg-card border border-border rounded-lg">
          <p className="text-muted-foreground">No navigation items yet</p>
        </div>
      )}
    </div>
  )
}

// ============== Main Dashboard ==============

const tabs: { id: TabType; label: string; icon: React.ElementType }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "cms", label: "CMS Editor", icon: FileText },
  { id: "theme", label: "Theme", icon: Palette },
  { id: "navigation", label: "Navigation", icon: Menu },
]

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>("overview")

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <LayoutDashboard className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-foreground">Admin Dashboard</h1>
                <p className="text-sm text-muted-foreground">Manage your platform</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar */}
          <div className="lg:col-span-1">
            <nav className="space-y-1">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      "w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-left",
                      activeTab === tab.id
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{tab.label}</span>
                    {activeTab === tab.id && (
                      <motion.div
                        layoutId="activeTab"
                        className="ml-auto w-1.5 h-1.5 rounded-full bg-primary-foreground"
                      />
                    )}
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Content */}
          <div className="lg:col-span-3">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="p-6 bg-card border border-border rounded-xl"
              >
                {activeTab === "overview" && <StatsPanel />}
                {activeTab === "cms" && <CmsEditor />}
                {activeTab === "theme" && <ThemeEditor />}
                {activeTab === "navigation" && <NavEditor />}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  )
}
