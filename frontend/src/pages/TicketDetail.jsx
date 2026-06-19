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
            const response = await api.get('/tickets/${id}');
            return response.data;
        },
    });

};

export default TicketDetail;