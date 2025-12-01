import axios from "axios";

export const api = axios.create({
    baseURL: "http://localhost:5000/api",
});

api.interceptors.response.use(
    (response) => {
        if (response.data?.success === false) {
            return Promise.reject({
                errorCode: response.data.errorCode,
                message: response.data.message,
            });
        }
        return response.data.data ?? response.data;
    },

    (error) => {
        if (error.response) {
            return Promise.reject({
                errorCode: error.response.data?.errorCode ?? "SERVER_ERROR",
                message: error.response.data?.message ?? "Неизвестная ошибка сервера",
            });
        }

        return Promise.reject({
            errorCode: "NETWORK_ERROR",
            message: "Нет соединения с сервером",
        });
    }
);
