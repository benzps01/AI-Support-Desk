import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';

const Tickets = () => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const [statusFilter, setStatusFilter] = useState('');

    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [newTicket, setNewTicket] = useState({ subject: '', body: '' });
    const [formError, setFormError] = useState('');

    const { data: tickets = [], isLoading, isError } = useQuery({
        queryKey: ["tickets", statusFilter],
        queryFn: async () => {
            const response = await api.get('/tickets', {
                params: statusFilter ? { status: statusFilter } : {},
            });
            return response.data;
        },
    });

    const createTicketMutation = useMutation({
        mutationFn: async (ticketData) => {
            const response = await api.post('/tickets', ticketData);
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['tickets'] }),
                setNewTicket({ subject: '', body: '' });
            setIsDrawerOpen(false);
            setFormError('');
        },
        onError: (err) => {
            setFormError(err.response?.data?.detail || 'Failed to create ticket. Try Again');
        },
    });

    const handleCreateSubmit = (e) => {
        e.preventDefault();
        if (!newTicket.subject.trim() || !newTicket.body.trim()) {
            setFormError('Subject and Description are required');
            return;
        }
        createTicketMutation.mutate(newTicket);
    };

    const getStatusBadge = (status) => {
        switch (status) {
            case 'open':
                return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
            case 'in-progress':
                return 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20';
            case 'resolved':
                return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
            case 'closed':
                return 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/20';
            default:
                return 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/20';
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 font-sans">
            {/* Navbar */}
            <header className="sticky top-0 z-40 backdrop-blur-md bg-slate-900/80 border-b border-slate-800">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                        <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                            <span className="font-bold text-white text-lg">A</span>
                        </div>
                        <span className="font-semibold text-lg tracking-tight bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
                            Ai Support Desk
                        </span>
                    </div>

                    <div className="flex items-center space-x-4">
                        <div className="text-right hidden sm:block">
                            <p className="text-xs text-slate-400">Signed In as</p>
                            <p className="text-sm font-medium text-slate-200 capitalize">{user?.role} User</p>
                        </div>
                        <button
                            onClick={logout}
                            className="px-3.5 py-1.5 rounded-lg text-sm font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700"
                        >
                            Sign Out
                        </button>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

                {/* Page title and Action Button */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
                    <div>
                        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">Tickets Dashboard</h1>
                        <p className="mt-1 text-sm text-slate-400">View and manage your support tickets.</p>
                    </div>

                    {user?.role === 'customer' && (
                        <button
                            onClick={() => setIsDrawerOpen(true)}
                            className="self-start sm:self-center px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg shadow-lg shadow-indigo-600/25 transition-all flex items-center space-x-2 cursor-pointer"
                        >
                            <span>+</span>
                            <span>New Ticket</span>
                        </button>
                    )}
                </div>

                {/* Filter Tabs */}
                <div className="flex border-b border-slate-800 mb-6 overflow-x-auto pb-1 gap-2">
                    {['', 'open', 'in_progress', 'resolved', 'closed'].map((status) => (
                        <button
                            key={status}
                            onClick={() => setStatusFilter(status)}
                            className="{`px-4 py-2 border-b-2 font-medium text-sm transition-all whitespace-nowrap cursor-pointer ${
                    statusFilter === status
                      ? 'border-indigo-500 text-indigo-400 font-semibold'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}"
                        >
                            {status === '' ? 'All Tickets' : status.replace('_', ' ').toUpperCase()}
                        </button>
                    ))}
                </div>

                {/* Loader, Error, list grid */}
                {isLoading ? (
                    <div className="flex justify-center py-20">
                        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-500"></div>
                    </div>
                ) : isError ? (
                    <div className="text-center py-20 bg-slate-900/50 rounded-2xl border border-red-500/20 max-w-lg mx-auto px-6">
                        <p className="text-red-400 font-medium">Failed to load tickets.</p>
                        <p className="text-xs text-slate-500 mt-1">Please try reloading the page.</p>
                    </div>
                ) : tickets.length === 0 ? (
                    <div className="text-center py-20 bg-slate-900/30 rounded-2xl border border-slate-800/80 max-w-lg mx-auto px-6">
                        <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center mx-auto mb-4 text-slate-500 text-xl font-bold">!</div>
                        <p className="text-slate-300 font-medium">No tickets found</p>
                        <p className="text-sm text-slate-500 mt-1">
                            {statusFilter ? `There are no tickets with status "${statusFilter}"` : "You haven't submitted any tickets yet."}
                        </p>
                        {user?.role === 'customer' && !statusFilter && (
                            <button
                                onClick={() => setIsDrawerOpen(true)}
                                className="mt-4 inline-flex items-center px-4 py-2 bg-indigo-600/20 hover:bg-indigo-600/35 text-indigo-400 border border-indigo-500/30 font-medium rounded-lg text-sm transition-colors cursor-pointer"
                            >
                                Create your first ticket
                            </button>
                        )}
                    </div>
                ) : (
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {tickets.map((ticket) => (
                            <div
                                key={ticket.id}
                                onClick={() => navigate(`/tickets/${ticket.id}`)}
                                className="group p-6 bg-slate-900/50 hover:bg-slate-900 border border-slate-800/80 hover:border-slate-700/80 rounded-2xl transition-all duration-300 cursor-pointer flex flex-col justify-between hover:shadow-xl
  hover:shadow-indigo-950/20"
                            >
                                <div>
                                    <div className="flex justify-between items-start mb-4 gap-2">
                                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${getStatusBadge(ticket.status)}`}>
                                            {ticket.status.replace('_', ' ')}
                                        </span>
                                        <span className="text-xs text-slate-500">
                                            #{ticket.id}
                                        </span>
                                    </div>

                                    <h3 className="text-lg font-semibold text-slate-100 group-hover:text-indigo-400 transition-colors line-clamp-1 mb-2">
                                        {ticket.subject}
                                    </h3>

                                    <p className="text-slate-400 text-sm line-clamp-3 mb-6">
                                        {ticket.body}
                                    </p>
                                </div>

                                <div className="border-t border-slate-800/80 pt-4 mt-auto flex items-center justify-between text-xs text-slate-500">
                                    <span>
                                        {new Date(ticket.created_at).toLocaleDateString()}
                                    </span>

                                    {ticket.priority && (
                                        <span className="px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 uppercase font-medium tracking-wide">
                                            {ticket.priority}
                                        </span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </main>

            {/* Slide out Drawer / Overlay for creating New Ticket */}
            {isDrawerOpen && (
                <div className="fixed inset-0 z-50 overflow-hidden" aria-labelledby="slide-over-title" role="dialog" aria-modal="true">
                    <div className="absolute inset-0 overflow-hidden">
                        {/* Backdrop */}
                        <div
                            className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm transition-opacity duration-300"
                            onClick={() => setIsDrawerOpen(false)}
                        ></div>

                        <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
                            <div className="pointer-events-auto w-screen max-w-md transform transition-all duration-300">
                                <div className="flex h-full flex-col bg-slate-900 border-l border-slate-800 shadow-2xl p-6">
                                    <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
                                        <h2 className="text-xl font-semibold text-white" id="slide-over-title">
                                            Create Support Ticket
                                        </h2>
                                        <button
                                            type="button"
                                            onClick={() => setIsDrawerOpen(false)}
                                            className="rounded-md text-slate-400 hover:text-slate-200 focus:outline-none"
                                        >
                                            <span className="text-2xl">&times;</span>
                                        </button>
                                    </div>

                                    {formError && (
                                        <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                                            {formError}
                                        </div>
                                    )}

                                    <form onSubmit={handleCreateSubmit} className="flex-1 flex flex-col justify-between">
                                        <div className="space-y-5">
                                            <div>
                                                <label htmlFor="subject" className="block text-sm font-medium text-slate-300 mb-1.5">
                                                    Subject
                                                </label>
                                                <input
                                                    type="text"
                                                    id="subject"
                                                    value={newTicket.subject}
                                                    onChange={(e) => setNewTicket({ ...newTicket, subject: e.target.value })}
                                                    placeholder="Brief summary of the problem"
                                                    className="w-full rounded-lg bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 px-3.5 py-2 text-slate-200 placeholder-slate-600 focus:outline-none text-sm
  transition-all"
                                                    required
                                                />
                                            </div>

                                            <div>
                                                <label htmlFor="body" className="block text-sm font-medium text-slate-300 mb-1.5">
                                                    Description
                                                </label>
                                                <textarea
                                                    id="body"
                                                    rows={6}
                                                    value={newTicket.body}
                                                    onChange={(e) => setNewTicket({ ...newTicket, body: e.target.value })}
                                                    placeholder="Describe the issue in detail..."
                                                    className="w-full rounded-lg bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 px-3.5 py-2 text-slate-200 placeholder-slate-600 focus:outline-none text-sm
  transition-all resize-none"
                                                    required
                                                />
                                            </div>
                                        </div>

                                        <div className="border-t border-slate-800 pt-6 mt-6 flex justify-end space-x-3">
                                            <button
                                                type="button"
                                                onClick={() => setIsDrawerOpen(false)}
                                                className="px-4 py-2 border border-slate-800 text-slate-400 hover:text-slate-200 font-medium rounded-lg text-sm transition-colors cursor-pointer"
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                type="submit"
                                                disabled={createTicketMutation.isPending}
                                                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg text-sm shadow-lg shadow-indigo-600/25 transition-all disabled:opacity-50 cursor-pointer"
                                            >
                                                {createTicketMutation.isPending ? 'Submitting...' : 'Submit Ticket'}
                                            </button>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Tickets;