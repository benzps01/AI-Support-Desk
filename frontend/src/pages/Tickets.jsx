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
        </div>
    )
};

export default Tickets;