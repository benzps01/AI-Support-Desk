import axios, { isCancel, AxiosError } from "axios";

const api = axios.create({
    baseURL: "http://localhost:8000"
});

const refreshApi = axios.create({
    baseURL: "http://localhost:8000"
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
    failedQueue.forEach((prom) => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token);
        }
    });
    failedQueue = [];
};

api.interceptors.request.use((config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
        config.headers.set("Authorization", `Bearer ${token}`);
    }
    return config;
})

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                })
                    .then((token) => {
                        originalRequest.headers["Authorization"] = `Bearer ${token}`;
                        return api(originalRequest);
                    })
                    .catch((err) => Promise.reject(err));
            }

            originalRequest._retry = true;
            isRefreshing = true;

            try {
                const { data } = await refreshApi.post("/auth/refresh", {
                    refresh_token: localStorage.getItem("refresh_token"),
                });

                const newToken = data.access_token;
                localStorage.setItem("access_token", newToken);
                api.defaults.headers.common["Authorization"] = `Bearer ${newToken}`;

                processQueue(null, newToken);

                originalRequest.headers["Authorization"] = `Bearer ${newToken}`;
                return api(originalRequest);
            } catch (refreshError) {
                processQueue(refreshError, null);
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token")
                window.location.href = "/login";
                return Promise.reject(refreshError);
            } finally {
                isRefreshing = false;
            }
        }
        return Promise.reject(error);
    }
);

export default api;