"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";

interface Ticket {
  id: string;
  title: string;
  category: string;
  status: string;
  priority: string;
  created_at: string;
  user: {
    username: string;
  };
}

interface TicketDetail extends Ticket {
  description: string;
  responses: TicketResponse[];
}

interface TicketResponse {
  id: string;
  content: string;
  is_internal: boolean;
  created_at: string;
  user: {
    username: string;
  };
}

const categories = [
  { value: "challenge_issue", label: "Challenge Issue - Is this broken?" },
  { value: "platform_bug", label: "Platform Bug" },
  { value: "account_issue", label: "Account Issue" },
  { value: "question", label: "General Question" },
  { value: "other", label: "Other" },
];

const priorities = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

export default function TicketsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<TicketDetail | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(true);

  // Form state
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    category: "question",
    priority: "medium",
    challenge_id: "",
  });
  const [responseText, setResponseText] = useState("");

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
      return;
    }
    if (status === "authenticated") {
      fetchTickets();
    }
  }, [status, router]);

  const fetchTickets = async () => {
    try {
      const res = await fetch("/api/tickets/my");
      const data = await res.json();
      setTickets(data);
    } catch (error) {
      console.error("Failed to fetch tickets:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTicketDetail = async (ticketId: string) => {
    try {
      const res = await fetch(`/api/tickets/my/${ticketId}`);
      const data = await res.json();
      setSelectedTicket(data);
    } catch (error) {
      console.error("Failed to fetch ticket detail:", error);
    }
  };

  const handleCreateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch("/api/tickets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (res.ok) {
        setShowCreateForm(false);
        setFormData({
          title: "",
          description: "",
          category: "question",
          priority: "medium",
          challenge_id: "",
        });
        fetchTickets();
      }
    } catch (error) {
      console.error("Failed to create ticket:", error);
    }
  };

  const handleRespond = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket) return;

    try {
      const res = await fetch(`/api/tickets/my/${selectedTicket.id}/respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: responseText }),
      });

      if (res.ok) {
        setResponseText("");
        fetchTicketDetail(selectedTicket.id);
      }
    } catch (error) {
      console.error("Failed to respond:", error);
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      open: "bg-yellow-500/20 text-yellow-400",
      in_progress: "bg-blue-500/20 text-blue-400",
      waiting_for_user: "bg-purple-500/20 text-purple-400",
      resolved: "bg-green-500/20 text-green-400",
      closed: "bg-gray-500/20 text-gray-400",
    };
    return colors[status] || colors.open;
  };

  const getPriorityColor = (priority: string) => {
    const colors: Record<string, string> = {
      low: "bg-gray-500/20 text-gray-400",
      medium: "bg-blue-500/20 text-blue-400",
      high: "bg-orange-500/20 text-orange-400",
      critical: "bg-red-500/20 text-red-400",
    };
    return colors[priority] || colors.medium;
  };

  if (status === "loading" || loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="text-cyan-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-200 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-cyan-400">Support Tickets</h1>
          <button
            onClick={() => setShowCreateForm(true)}
            className="px-6 py-2 bg-cyan-500/20 border border-cyan-500/50 text-cyan-400 rounded-lg hover:bg-cyan-500/30 transition-colors"
          >
            + New Ticket
          </button>
        </div>

        {showCreateForm && (
          <div className="mb-8 p-6 bg-[#12121a] border border-gray-800 rounded-xl">
            <h2 className="text-xl font-semibold text-cyan-400 mb-4">
              Create New Ticket
            </h2>
            <form onSubmit={handleCreateTicket} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Title</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) =>
                    setFormData({ ...formData, title: e.target.value })
                  }
                  className="w-full px-4 py-2 bg-[#0a0a0f] border border-gray-700 rounded-lg focus:border-cyan-500 focus:outline-none"
                  placeholder="Brief description of the issue"
                  required
                  minLength={5}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    Category
                  </label>
                  <select
                    value={formData.category}
                    onChange={(e) =>
                      setFormData({ ...formData, category: e.target.value })
                    }
                    className="w-full px-4 py-2 bg-[#0a0a0f] border border-gray-700 rounded-lg focus:border-cyan-500 focus:outline-none"
                  >
                    {categories.map((cat) => (
                      <option key={cat.value} value={cat.value}>
                        {cat.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    Priority
                  </label>
                  <select
                    value={formData.priority}
                    onChange={(e) =>
                      setFormData({ ...formData, priority: e.target.value })
                    }
                    className="w-full px-4 py-2 bg-[#0a0a0f] border border-gray-700 rounded-lg focus:border-cyan-500 focus:outline-none"
                  >
                    {priorities.map((pri) => (
                      <option key={pri.value} value={pri.value}>
                        {pri.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  className="w-full px-4 py-2 bg-[#0a0a0f] border border-gray-700 rounded-lg focus:border-cyan-500 focus:outline-none h-32"
                  placeholder="Detailed description of your issue or question..."
                  required
                  minLength={10}
                />
              </div>

              <div className="flex gap-4">
                <button
                  type="submit"
                  className="px-6 py-2 bg-cyan-500 text-black font-medium rounded-lg hover:bg-cyan-400 transition-colors"
                >
                  Submit Ticket
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="px-6 py-2 border border-gray-600 text-gray-400 rounded-lg hover:border-gray-500 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Ticket List */}
          <div className="lg:col-span-1 space-y-4">
            <h2 className="text-lg font-semibold text-gray-300">Your Tickets</h2>
            {tickets.length === 0 ? (
              <div className="p-8 text-center bg-[#12121a] border border-gray-800 rounded-xl">
                <p className="text-gray-500">No tickets yet</p>
                <p className="text-sm text-gray-600 mt-1">
                  Create a ticket if you need help!
                </p>
              </div>
            ) : (
              tickets.map((ticket) => (
                <div
                  key={ticket.id}
                  onClick={() => fetchTicketDetail(ticket.id)}
                  className={`p-4 bg-[#12121a] border rounded-xl cursor-pointer transition-all hover:border-cyan-500/50 ${
                    selectedTicket?.id === ticket.id
                      ? "border-cyan-500"
                      : "border-gray-800"
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-medium text-gray-200 line-clamp-1">
                      {ticket.title}
                    </h3>
                  </div>
                  <div className="flex gap-2 text-xs">
                    <span
                      className={`px-2 py-1 rounded ${getStatusColor(
                        ticket.status
                      )}`}
                    >
                      {ticket.status.replace("_", " ")}
                    </span>
                    <span
                      className={`px-2 py-1 rounded ${getPriorityColor(
                        ticket.priority
                      )}`}
                    >
                      {ticket.priority}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    {new Date(ticket.created_at).toLocaleDateString()}
                  </p>
                </div>
              ))
            )}
          </div>

          {/* Ticket Detail */}
          <div className="lg:col-span-2">
            {selectedTicket ? (
              <div className="bg-[#12121a] border border-gray-800 rounded-xl p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-xl font-semibold text-cyan-400 mb-2">
                      {selectedTicket.title}
                    </h2>
                    <div className="flex gap-2 text-sm">
                      <span
                        className={`px-2 py-1 rounded ${getStatusColor(
                          selectedTicket.status
                        )}`}
                      >
                        {selectedTicket.status.replace("_", " ")}
                      </span>
                      <span
                        className={`px-2 py-1 rounded ${getPriorityColor(
                          selectedTicket.priority
                        )}`}
                      >
                        {selectedTicket.priority}
                      </span>
                      <span className="px-2 py-1 rounded bg-gray-700/50 text-gray-400">
                        {selectedTicket.category.replace("_", " ")}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedTicket(null)}
                    className="text-gray-500 hover:text-gray-300"
                  >
                    ✕
                  </button>
                </div>

                <div className="mb-6 p-4 bg-[#0a0a0f] rounded-lg">
                  <p className="text-gray-300 whitespace-pre-wrap">
                    {selectedTicket.description}
                  </p>
                </div>

                {/* Responses */}
                <div className="space-y-4 mb-6">
                  <h3 className="font-medium text-gray-300">Responses</h3>
                  {selectedTicket.responses.length === 0 ? (
                    <p className="text-gray-500 text-sm">
                      No responses yet. Our team will respond soon!
                    </p>
                  ) : (
                    selectedTicket.responses
                      .filter((r) => !r.is_internal)
                      .map((response) => (
                        <div
                          key={response.id}
                          className={`p-4 rounded-lg ${
                            response.user.username ===
                            selectedTicket.user.username
                              ? "bg-cyan-500/10 border border-cyan-500/20"
                              : "bg-purple-500/10 border border-purple-500/20"
                          }`}
                        >
                          <div className="flex justify-between items-start mb-2">
                            <span className="text-sm font-medium text-gray-300">
                              {response.user.username}
                              {response.user.username !==
                                selectedTicket.user.username && (
                                <span className="ml-2 text-xs text-purple-400">
                                  (Admin)
                                </span>
                              )}
                            </span>
                            <span className="text-xs text-gray-500">
                              {new Date(response.created_at).toLocaleString()}
                            </span>
                          </div>
                          <p className="text-gray-300 whitespace-pre-wrap">
                            {response.content}
                          </p>
                        </div>
                      ))
                  )}
                </div>

                {/* Reply Form */}
                {selectedTicket.status !== "closed" &&
                  selectedTicket.status !== "resolved" && (
                    <form onSubmit={handleRespond} className="space-y-3">
                      <textarea
                        value={responseText}
                        onChange={(e) => setResponseText(e.target.value)}
                        className="w-full px-4 py-2 bg-[#0a0a0f] border border-gray-700 rounded-lg focus:border-cyan-500 focus:outline-none h-24"
                        placeholder="Add a response..."
                        required
                      />
                      <button
                        type="submit"
                        className="px-4 py-2 bg-cyan-500 text-black font-medium rounded-lg hover:bg-cyan-400 transition-colors"
                      >
                        Send Response
                      </button>
                    </form>
                  )}
              </div>
            ) : (
              <div className="h-full flex items-center justify-center bg-[#12121a] border border-gray-800 rounded-xl p-12">
                <div className="text-center">
                  <p className="text-gray-500 mb-2">Select a ticket to view details</p>
                  <p className="text-sm text-gray-600">
                    Or create a new ticket to get help
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
