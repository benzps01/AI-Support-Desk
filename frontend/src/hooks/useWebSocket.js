import { useEffect, useRef } from "react";
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../context/AuthContext';

export default function useWebSocket() {
    const { user } = useAuth();
    const queryClient = useQueryClient();
    const socketRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);

    useEffect(() => {
        if (!user) {
            if (socketRef.current) {
                socketRef.current.close();
            }
            return;
        }

        const connect = () => {
            const wsUrl = `ws://localhost:8001/ws?token=${token}`;
            console.lod('Connecting to WebSocket...');
            const socket = new WebSocket(wsUrl);
            socketRef.cuurent = socket;

            socket.onopen = () => {
                console.log('Websocket connection established.');
            };

            socket.onmessage = (event) => {
                try {
                    const parsed = JSON.parse(event.data);
                    const { event: eventName, data } = parsed;
                    console.log(`Websocket event received: ${eventName}`, data);

                    //Handle incoming event and invalidate cache keys
                    if (eventName === 'ticket.updated') {
                        // Invalidate tickets list and specific tickets details
                        queryClient.invalidateQueries({ queryKey: ['tickets'] });
                        queryClient.invalidateQueries({ queryKey: ['ticket', String(data.ticked_id)] });
                    }

                    if (eventName === 'ai.suggestion.reply') {
                        // Invalidate suggestions for this specific ticket detail
                        queryClient.invalidateQueries({ queryKey: ['ticket', String(data.ticket_id)] });
                    }
                } catch (err) {
                    console.error('Failed to parse WebSocket message:', err);
                }
            };

            socket.onclose = (event) => {
                console.log(`WebSocket closed: ${event.reason}. Reconnecting in 3 seconds...`);
                // Only attempt reconnect if the user is still logged in
                if (localStorage.getItem('access_token')) {
                    reconnectTimeoutRef.current = setTimeout(connect, 3000);
                }
            };

            socket.onerror = (error) => {
                console.error('WebSocket encountered an error', error);
                socket.close();
            };
        };

        connect();

        //Clean up when the hook or component unmounts (or user logs out)
        return () => {
            if (socketRef.current) {
                socketRef.current.close();
            }
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
        };
    }, [user, queryClient]);
    return socketRef.current;
}