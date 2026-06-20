import React, { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../context/AuthContext";
import api from "../api/client";

const TicketDetail = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { user } = useAuth();

    const [replyBody, setReplyBody] = useState('');
    const [isInternalNote, setIsInternalNote] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');

    //1. Fetch Ticket details and message
    const { data: ticket, isLoading, isError } = useQuery({
        queryKey: ['ticket', id],
        queryFn: async () => {
            const response = await api.get(`/tickets/${id}`);
            return response.data;
        },
    });

    // 2. Mutation to post new message
    const postMessageMutation = useMutation({
        mutationFn: async (messageData) => {
            const response = await api.post(`/tickets/${id}/messages`, messageData);
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['ticket', id] });
            setReplyBody('');
            setIsInternalNote(false);
            setErrorMessage('');
        },
        onError: (err) => {
            setErrorMessage(err.response?.data?.detail || 'Failed to send message');
        },
    });

    // 3. Mutation to update ticket status
    const updateTicketMutation = useMutation({
        mutationFn: async (updatedFields) => {
            const response = await api.patch(`/tickets/${id}`, updatedFields);
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['ticket', id] });
            queryClient.invalidateQueries({ queryKey: ['tickets'] });
            setErrorMessage('')
        },
        onError: (err) => {
            setErrorMessage(err.response?.data?.detail || 'Failed to update ticket status.');
        },
    });

    const handleMessageSubmit = (e) => {
        e.preventDefault();
        if (!replyBody.trim()) return;

        postMessageMutation.mutate({
            body: replyBody,
            is_internal_note: isInternalNote,
        });
    };

    const handleStatusChange = (newStatus) => {
        updateTicketMutation.mutate({ status: newStatus });
    };


    // status badge color helper
    const getStatusBadge = (status) => {
        switch (status) {
            case 'open':
                return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
            case 'in_progress':
                return 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20';
            case 'resolved':
                return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
            case 'closed':
                return 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/20';
            default:
                return 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/20';
        }
    };


    if (isLoading) {
        return (
            <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-500"></div>
            </div>
        );
    }

    if (isError || !ticket) {
        return (
            <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6">
                <div className="text-center py-8 bg-slate-900/50 rounded-2xl border border-red-500/20 max-w-md px-6">
                    <p className="text-red-400 font-medium">Ticket not found or access denied</p>
                    <Link
                        to='/tickets'
                        className="mt-4 inline-block text-sm text-indigo-400 hover:text-indigo-300 font-semibold">
                        &larr; Back to Dashboard
                    </Link>
                </div>
            </div>
        );
    }


    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 font-sans pb-12">
            {/* Header Bar */}
            <header className="sticky top-0 z-40 backdrop-blur-md bg-slate-900/80 border-b border-slate-800">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                    <Link
                        to='/tickets'
                        className="text-sm font-medium text-slate-400 hover:text-slate-200 transition-colors flex items-center space-x-2"
                    >
                        <span>&larr;</span> <span>Back to Dashboard</span>
                    </Link>
                    <span className="text-xs text-slate-500 uppercase tracking-widest font-semibold">
                        Ticket ID: #{ticket.id}
                    </span>
                </div>
            </header>

            <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {errorMessage && (
                    <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                        {errorMessage}
                    </div>
                )}

                {/* Ticket Detail Block */}
                <section className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-6 sm:p-8 mb-8">
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
                        <div>
                            <div className="flex items-center space-x-3 mb-2 flex-wrap gap-y-2">
                                <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${getStatusBadge(ticket.status)}`}>
                                    {ticket.status.replace('_', ' ')}
                                </span>
                                {ticket.priority && (
                                    <span className="px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 text-xs font-medium uppercase">
                                        {ticket.priority} Priority
                                    </span>
                                )}
                                {ticket.category && (
                                    <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-xs font-medium uppercase">
                                        {ticket.category}
                                    </span>
                                )}
                            </div>
                            <h1 className="text-xl sm:text-2xl font-bold text-white leading-tight">
                                {ticket.subject}
                            </h1>
                            <p className="text-xs text-slate-500 mt-1">
                                Submitted on {new Date(ticket.created_at).toLocaleString()}
                            </p>
                        </div>

                        {/* Status Change Dropdown for staff */}
                        {user?.role !== 'customer' && (
                            <div className="flex flex-col items-start sm:items-end gap-1.5">
                                <label className="text-xs text-slate-400 font-medium">Update Status</label>
                                <select
                                    value={ticket.status}
                                    onChange={(e) => handleStatusChange(e.target.value)}
                                    className="rounded-lg bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 px-3 py-1.
  5 text-sm text-slate-200 focus:outline-none transition-all cursor-pointer"
                                >
                                    <option value="open">Open</option>
                                    <option value="in_progress">In Progress</option>
                                    <option value="resolved">Resolved</option>
                                    <option value="closed">Closed</option>
                                </select>
                            </div>
                        )}
                    </div>

                    <div className="prose prose-invert max-w-none text-slate-300 border-t border-slate-800/80 pt-6 whitespace-pre-wrap text-sm leading-relaxed">
                        {ticket.body}
                    </div>
                </section>

                {/* Thread History Section */}
                <section className="space-y-6 mb-8">
                    <h2 className="text-lg font-semibold text-white tracking-tight border-b border-slate-800 pb-3">
                        Activity & Discussion
                    </h2>

                    <div className="space-y-4">
                        {ticket.messages
                            //Client security side-check: screen out internal notes for customers
                            .filter((msg) => !(msg.is_internal_note && user?.role === 'customer'))
                            .map((msg) => {
                                const isSystemMessage = msg.sender_id === 0;

                                if (isSystemMessage) {
                                    return (
                                        <div key={msg.id} className="text-center py-2">
                                            <span className="px-3 py-1 bg-slate-900/60 rounded-full text-xs text-slate-500 border border-slate-800/50">
                                                {msg.body}
                                            </span>
                                        </div>
                                    );
                                }

                                // Decide color schemes based on note type or sender
                                const msgClasses = msg.is_internal_note
                                    ? 'bg-amber-500/10 border-amber-500/20 text-amber-200 ml-6 sm:ml-12'
                                    : user?.id === msg.sender_id
                                        ? 'bg-indigo-600/10 border-indigo-500/20 text-indigo-200 ml-6 sm:ml-12'
                                        : 'bg-slate-900/50 border-slate-800 text-slate-300 mr-6 sm:mr-12';

                                return (
                                    <div
                                        key={msg.id}
                                        className={`p-4 rounded-xl border flex flex-col justify-between transition-all ${msgClasses}`}
                                    >
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center space-x-2">
                                                <span className="text-xs font-semibold text-slate-400">
                                                    {user?.id === msg.sender_id ? 'You' : `User #${msg.sender_id}`}
                                                </span>
                                                {msg.is_internal_note && (
                                                    <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                                                        Internal Note (Staff Only)
                                                    </span>
                                                )}
                                            </div>
                                            <span className="text-[10px] text-slate-500">
                                                {new Date(msg.created_at).toLocaleString([], { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                        </div>
                                        <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.body}</p>
                                    </div>
                                );
                            })
                        }
                    </div>
                </section>

                {/* Reply Editor Form */}
                <section className="bg-slate-900/30 border border-slate-800/80 rounded-2xl p-6">
                    <form onSubmit={handleMessageSubmit} className="space-y-4">
                        <div>
                            <label htmlFor="reply" className="block text-sm font-medium text-slate-300 mb-1.5">
                                Post a Reply
                            </label>
                            <textarea
                                id="reply"
                                rows={4}
                                value={replyBody}
                                onChange={(e) => setReplyBody(e.target.value)}
                                placeholder="Type your message here...."
                                className="w-full rounded-lg bg-slate-950 border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 px-3.5 py-2 text-slate-200 placeholder-slate-600 focus:outline-none text-sm transition-all resize-none"
                                required
                                disabled={postMessageMutation.isPending}
                            />
                        </div>

                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                            {/* Internal note checkbox ( Restricted to Staff only ) */}
                            {user?.role !== 'customer' ? (
                                <div className="flex items-center">
                                    <input
                                        id="internal_note"
                                        type="checkbox"
                                        checked={isInternalNote}
                                        onChange={(e) => setIsInternalNote(e.target.checked)}
                                        className="h-4 w-4 rounded border-slate-800 bg-slate-950 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-0 focus:outline-none"
                                    />
                                    <label htmlFor="internal_note" className="ml-2 text-sm text-slate-400 cursor-pointer select-none">
                                        Mark as Internal note (Staff Only)
                                    </label>
                                </div>
                            ) : (
                                <div />
                            )}

                            <button
                                type="submit"
                                disabled={postMessageMutation.isPending || !replyBody.trim()}
                                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg text-sm shadow-lg shadow-indigo-600/25 transition-all disabled:opacity-50 cursor-pointer self-end"
                            >
                                {postMessageMutation.isPending ? 'Sending...' : 'Send Message'}
                            </button>
                        </div>
                    </form>
                </section>
            </main>
        </div>
    );
};

export default TicketDetail;