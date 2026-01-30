"use client"

import { useState, useMemo } from "react"
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  flexRender,
  type SortingState,
  type ColumnDef,
} from "@tanstack/react-table"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import { motion } from "framer-motion"
import {
  Trophy,
  TrendingUp,
  Users,
  Target,
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Medal,
} from "lucide-react"

// Types
interface Team {
  id: string
  rank: number
  name: string
  score: number
  solved: number
  members: number
  accuracy: number
  trend: number[]
  lastSubmission: string
}

// Mock data for leaderboard
const mockTeams: Team[] = [
  {
    id: "1",
    rank: 1,
    name: "CyberSentinels",
    score: 15420,
    solved: 47,
    members: 5,
    accuracy: 94.2,
    trend: [12000, 12500, 13200, 13800, 14200, 14800, 15420],
    lastSubmission: "2 mins ago",
  },
  {
    id: "2",
    rank: 2,
    name: "PhantomPhreaks",
    score: 14850,
    solved: 45,
    members: 4,
    accuracy: 91.8,
    trend: [11000, 11800, 12500, 13200, 13800, 14300, 14850],
    lastSubmission: "15 mins ago",
  },
  {
    id: "3",
    rank: 3,
    name: "ZeroDayZombies",
    score: 14200,
    solved: 43,
    members: 6,
    accuracy: 89.5,
    trend: [10500, 11200, 11800, 12500, 13200, 13800, 14200],
    lastSubmission: "32 mins ago",
  },
  {
    id: "4",
    rank: 4,
    name: "BinaryBandits",
    score: 13800,
    solved: 42,
    members: 5,
    accuracy: 92.1,
    trend: [10000, 10800, 11500, 12200, 12800, 13300, 13800],
    lastSubmission: "1 hour ago",
  },
  {
    id: "5",
    rank: 5,
    name: "PacketPirates",
    score: 13250,
    solved: 40,
    members: 4,
    accuracy: 87.3,
    trend: [9500, 10200, 11000, 11800, 12400, 12800, 13250],
    lastSubmission: "1.5 hours ago",
  },
  {
    id: "6",
    rank: 6,
    name: "HashHunters",
    score: 12800,
    solved: 39,
    members: 5,
    accuracy: 88.9,
    trend: [9000, 9800, 10500, 11200, 11800, 12300, 12800],
    lastSubmission: "2 hours ago",
  },
  {
    id: "7",
    rank: 7,
    name: "RootRunners",
    score: 12400,
    solved: 38,
    members: 4,
    accuracy: 85.7,
    trend: [8800, 9500, 10200, 10800, 11400, 11900, 12400],
    lastSubmission: "2.5 hours ago",
  },
  {
    id: "8",
    rank: 8,
    name: "CipherSeekers",
    score: 11950,
    solved: 36,
    members: 5,
    accuracy: 84.2,
    trend: [8500, 9200, 9800, 10400, 11000, 11500, 11950],
    lastSubmission: "3 hours ago",
  },
  {
    id: "9",
    rank: 9,
    name: "ExploitElite",
    score: 11500,
    solved: 35,
    members: 4,
    accuracy: 86.4,
    trend: [8000, 8700, 9400, 10000, 10600, 11100, 11500],
    lastSubmission: "3.5 hours ago",
  },
  {
    id: "10",
    rank: 10,
    name: "MalwareMasters",
    score: 11100,
    solved: 34,
    members: 6,
    accuracy: 82.1,
    trend: [7800, 8400, 9000, 9600, 10200, 10700, 11100],
    lastSubmission: "4 hours ago",
  },
]

// Race graph data - showing score progression over time
const raceData = [
  { time: "Start", CyberSentinels: 12000, PhantomPhreaks: 11000, ZeroDayZombies: 10500 },
  { time: "Hour 1", CyberSentinels: 12500, PhantomPhreaks: 11800, ZeroDayZombies: 11200 },
  { time: "Hour 2", CyberSentinels: 13200, PhantomPhreaks: 12500, ZeroDayZombies: 11800 },
  { time: "Hour 3", CyberSentinels: 13800, PhantomPhreaks: 13200, ZeroDayZombies: 12500 },
  { time: "Hour 4", CyberSentinels: 14200, PhantomPhreaks: 13800, ZeroDayZombies: 13200 },
  { time: "Hour 5", CyberSentinels: 14800, PhantomPhreaks: 14300, ZeroDayZombies: 13800 },
  { time: "Hour 6", CyberSentinels: 15420, PhantomPhreaks: 14850, ZeroDayZombies: 14200 },
]

const getRankIcon = (rank: number) => {
  switch (rank) {
    case 1:
      return <Medal className="w-6 h-6 text-yellow-400" />
    case 2:
      return <Medal className="w-6 h-6 text-gray-400" />
    case 3:
      return <Medal className="w-6 h-6 text-amber-600" />
    default:
      return <span className="text-muted-foreground font-mono">#{rank}</span>
  }
}

const columns: ColumnDef<Team>[] = [
  {
    accessorKey: "rank",
    header: "Rank",
    cell: ({ row }) => (
      <div className="flex items-center justify-center w-10">
        {getRankIcon(row.original.rank)}
      </div>
    ),
  },
  {
    accessorKey: "name",
    header: "Team",
    cell: ({ row }) => (
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center border border-primary/20">
          <span className="text-sm font-bold text-primary">
            {row.original.name.slice(0, 2).toUpperCase()}
          </span>
        </div>
        <span className="font-semibold">{row.original.name}</span>
      </div>
    ),
  },
  {
    accessorKey: "score",
    header: ({ column }) => (
      <button
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        className="flex items-center gap-1 hover:text-primary transition-colors"
      >
        <Trophy className="w-4 h-4" />
        Score
        {column.getIsSorted() === "asc" ? (
          <ChevronUp className="w-3 h-3" />
        ) : column.getIsSorted() === "desc" ? (
          <ChevronDown className="w-3 h-3" />
        ) : null}
      </button>
    ),
    cell: ({ row }) => (
      <span className="font-mono font-bold text-primary">
        {row.original.score.toLocaleString()}
      </span>
    ),
  },
  {
    accessorKey: "solved",
    header: ({ column }) => (
      <button
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        className="flex items-center gap-1 hover:text-primary transition-colors"
      >
        <Target className="w-4 h-4" />
        Solved
        {column.getIsSorted() === "asc" ? (
          <ChevronUp className="w-3 h-3" />
        ) : column.getIsSorted() === "desc" ? (
          <ChevronDown className="w-3 h-3" />
        ) : null}
      </button>
    ),
    cell: ({ row }) => (
      <span className="font-mono">{row.original.solved}</span>
    ),
  },
  {
    accessorKey: "members",
    header: ({ column }) => (
      <button
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        className="flex items-center gap-1 hover:text-primary transition-colors"
      >
        <Users className="w-4 h-4" />
        Members
        {column.getIsSorted() === "asc" ? (
          <ChevronUp className="w-3 h-3" />
        ) : column.getIsSorted() === "desc" ? (
          <ChevronDown className="w-3 h-3" />
        ) : null}
      </button>
    ),
    cell: ({ row }) => row.original.members,
  },
  {
    accessorKey: "accuracy",
    header: ({ column }) => (
      <button
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        className="flex items-center gap-1 hover:text-primary transition-colors"
      >
        <TrendingUp className="w-4 h-4" />
        Accuracy
        {column.getIsSorted() === "asc" ? (
          <ChevronUp className="w-3 h-3" />
        ) : column.getIsSorted() === "desc" ? (
          <ChevronDown className="w-3 h-3" />
        ) : null}
      </button>
    ),
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary to-primary/50 rounded-full"
            style={{ width: `${row.original.accuracy}%` }}
          />
        </div>
        <span className="text-sm text-muted-foreground">
          {row.original.accuracy}%
        </span>
      </div>
    ),
  },
  {
    accessorKey: "lastSubmission",
    header: "Last Submission",
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {row.original.lastSubmission}
      </span>
    ),
  },
]

export default function LeaderboardPage() {
  const [sorting, setSorting] = useState<SortingState>([
    { id: "score", desc: true },
  ])

  const table = useReactTable({
    data: mockTeams,
    columns,
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: {
        pageSize: 10,
      },
    },
  })

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-primary to-primary/50 bg-clip-text text-transparent">
            Leaderboard
          </h1>
          <p className="text-muted-foreground">
            Compete with the best teams and climb to the top
          </p>
        </motion.div>

        {/* Race Graph - Top Teams */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8 p-6 rounded-xl border border-border bg-card/50 backdrop-blur-sm"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-lg bg-primary/10">
              <TrendingUp className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-semibold">Race to the Top</h2>
              <p className="text-sm text-muted-foreground">
                Score progression of top 3 teams over time
              </p>
            </div>
          </div>

          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={raceData}>
                <defs>
                  <linearGradient id="colorCyber" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorPhantom" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorZero" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="time"
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={12}
                />
                <YAxis
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={12}
                  tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                  }}
                  labelStyle={{ color: "hsl(var(--foreground))" }}
                />
                <Area
                  type="monotone"
                  dataKey="CyberSentinels"
                  stroke="#3b82f6"
                  fillOpacity={1}
                  fill="url(#colorCyber)"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="PhantomPhreaks"
                  stroke="#8b5cf6"
                  fillOpacity={1}
                  fill="url(#colorPhantom)"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="ZeroDayZombies"
                  stroke="#10b981"
                  fillOpacity={1}
                  fill="url(#colorZero)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-6 mt-4 justify-center">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              <span className="text-sm">CyberSentinels</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-violet-500" />
              <span className="text-sm">PhantomPhreaks</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-emerald-500" />
              <span className="text-sm">ZeroDayZombies</span>
            </div>
          </div>
        </motion.div>

        {/* Leaderboard Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-xl border border-border bg-card/50 backdrop-blur-sm overflow-hidden"
        >
          <div className="p-4 border-b border-border">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Team Rankings</h2>
              <span className="text-sm text-muted-foreground">
                {mockTeams.length} teams competing
              </span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id} className="border-b border-border">
                    {headerGroup.headers.map((header) => (
                      <th
                        key={header.id}
                        className="px-4 py-3 text-left text-sm font-medium text-muted-foreground"
                      >
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row, index) => (
                  <motion.tr
                    key={row.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="border-b border-border hover:bg-muted/50 transition-colors"
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3">
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </td>
                    ))}
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="p-4 border-t border-border flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Page {table.getState().pagination.pageIndex + 1} of{" "}
              {table.getPageCount()}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                className="p-2 rounded-lg border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                className="p-2 rounded-lg border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
